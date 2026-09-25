// Copyright (c) 2026, SriRagul and contributors
// For license information, please see license.txt

frappe.ui.form.on("Class Session", {
    setup(frm) {
        frm.set_query("trainer", () => {
            let filters = { status: "Active" };

            if (frm.doc.session_type) {
                filters.specialization = frm.doc.session_type;
            }

            return { filters };
        });

        frm.set_query("package_purchase", "attendees", (doc, cdt, cdn) => {
            let row = locals[cdt][cdn];
            return { filters: { member: row.member, status: "Active" } };
        });
    },
    refresh(frm) {
        if (frm.doc.status === "Draft") {
            frm.dashboard.add_indicator("Draft", "orange");
        }

        if (frm.doc.status === "Scheduled") {
            frm.dashboard.add_indicator("Scheduled", "blue");
        }

        if (frm.doc.status === "Completed") {
            frm.dashboard.add_indicator("Completed", "green");
        }

        if (frm.doc.status === "Cancelled") {
            frm.dashboard.add_indicator("Cancelled", "red");
        }

        if (frm.doc.status === "Scheduled" && frm.doc.session_date <= frappe.datetime.get_today()) {
            frm.add_custom_button("Finalize Session", () => {
                frm.set_value("status", "Completed");
                frm.save();
            });
        }

        frm.add_custom_button("Cancel Session", () => {
            let dialog = new frappe.ui.Dialog({
                title: "Cancel Session",
                fields: [
                    {
                        fieldname: "reason",
                        fieldtype: "Small Text",
                        label: "Cancellation Reason",
                        reqd: 1
                    }
                ],
                primary_action_label: "Cancel Session",
                primary_action(values) {
                    frm.set_value("cancellation_reason", values.reason);
                    frm.set_value("status", "Cancelled");
                    dialog.hide();
                    frm.save();
                }
            });

            dialog.show();
        });

        frm.add_custom_button("Swap Trainer", () => {
            frappe.prompt(
                {
                    fieldname: "trainer",
                    fieldtype: "Link",
                    options: "Trainer",
                    label: "Trainer",
                    reqd: 1
                },
                (values) => {
                    frappe.confirm("Swap trainer for this session?", () => {
                        frappe.call({
                            method: "frappe.client.set_value",
                            args: {
                                doctype: "Class Session",
                                name: frm.doc.name,
                                fieldname: "trainer",
                                value: values.trainer
                            },
                            callback() {
                                frm.reload_doc();
                                frm.trigger("trainer");
                            }
                        });
                    });
                },
                "Swap Trainer",
                "Swap"
            );
        });
    },

    trainer(frm) {
        frm.set_query("trainer", () => {
            let filters = { status: "Active" };

            if (frm.doc.session_type) {
                filters.specialization = frm.doc.session_type;
            }

            return { filters };
        });
    }
});

frappe.ui.form.on("Attendee Entry", {
    member(frm, cdt, cdn) {
        frappe.model.set_value(cdt, cdn, "package_purchase", "");
        frappe.model.set_value(cdt, cdn, "credits_remaining", 0);
    },
    package_purchase(frm, cdt, cdn) {
        update_attendee_balance(frm, cdt, cdn);
    }
});

function update_attendee_balance(frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);

    if (!row.package_purchase) {
        frappe.model.set_value(cdt, cdn, "credits_remaining", 0);
        return;
    }

    frappe.db.get_value(
        "Package Purchase",
        row.package_purchase,
        ["credits_remaining"],
        (r) => {
            let balance = (r.message && r.message.credits_remaining) || 0;
            frappe.model.set_value(cdt, cdn, "credits_remaining", balance);

            if (!frm.doc.session_type) {
                return;
            }

            frappe.db.get_value(
                "Session Type",
                frm.doc.session_type,
                ["credits_required"],
                (res) => {
                    let needed = (res.message && res.message.credits_required) || 0;

                    if (balance < needed) {
                        frappe.msgprint(`${row.member} has only ${balance} credits left`);
                    }
                }
            );
        }
    );
}
