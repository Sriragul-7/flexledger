# Copyright (c) 2026, SriRagul and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ClassSession(Document):

    def validate(self):
        session_date = frappe.utils.getdate(self.session_date)

        if self.status == "Draft" and session_date < frappe.utils.getdate():
            frappe.throw("Session Date can not be in the past")

        credits_required = frappe.db.get_value("Session Type", self.session_type, "credits_required")
        if not credits_required:
            frappe.throw("Invalid Session Type")

        for row in self.attendees:
            package = frappe.db.get_value(
                "Package Purchase",
                row.package_purchase,
                ["member", "status", "expiry_date", "credits_remaining"],
                as_dict=True,
            )
            if not package:
                frappe.throw("Invalid Package")
            if package.member != row.member:
                frappe.throw("Package does not belong to member")
            if package.status != "Active":
                frappe.throw("Package is not Active")
            if frappe.utils.getdate(package.expiry_date) < session_date:
                frappe.throw("Package is expired")
            if package.credits_remaining < credits_required:
                frappe.throw(f"{row.member} has only {package.credits_remaining} credits left")

            row.credits_charged = credits_required

    def before_submit(self):
        if self.status != "Completed":
            frappe.throw("Status must be Completed")

        for row in self.attendees:
            if row.attendance_status == "Booked":
                frappe.throw("Attendance not finalized")

    def on_submit(self):
        if self.credits_deducted:
            return

        for row in self.attendees:
            if self.is_charged(row):
                self.deduct_credits(row)

        self.db_set("credits_deducted", 1, update_modified=False)

    def on_cancel(self):
        if self.credits_deducted:
            for row in self.attendees:
                if self.is_charged(row):
                    self.refund_credits(row)

            self.db_set("credits_deducted", 0, update_modified=False)

        self.db_set("status", "Cancelled", update_modified=False)

    def on_trash(self):
        if self.status not in ("Cancelled", "Draft"):
            frappe.throw("Only Draft or Cancelled can be deleted")

    def is_charged(self, row):
        if row.attendance_status == "Attended":
            return True
        if row.attendance_status == "No-Show" and frappe.db.get_single_value(
            "Studio Settings", "no_show_forfeits_credit"
        ):
            return True
        return False

    def deduct_credits(self, row):
        package = frappe.db.get_value(
            "Package Purchase",
            row.package_purchase,
            ["credits_used", "total_credits"],
            as_dict=True,
        )

        credits_used = package.credits_used + row.credits_charged
        credits_remaining = package.total_credits - credits_used

        # set_value writes straight to the table: no permission check, no document events.
        # That bypass is acceptable here because submit already passed the user's permission
        # check and validate() approved this exact amount against this member's own package —
        # the row and the amount are never chosen by the person clicking submit.
        frappe.db.set_value(
            "Package Purchase",
            row.package_purchase,
            {
                "credits_used": credits_used,
                "credits_remaining": credits_remaining,
                "status": "Fully Used" if credits_remaining == 0 else "Active",
            },
        )

        threshold = frappe.db.get_single_value("Studio Settings", "low_balance_alert_threshold")
        if threshold and credits_remaining <= threshold:
            frappe.enqueue(
                "flexledger.notifications.send_low_balance_email",
                queue="short",
                member=row.member,
                package_name=row.package_purchase,
                credits_remaining=credits_remaining,
            )

    def refund_credits(self, row):
        package = frappe.db.get_value(
            "Package Purchase",
            row.package_purchase,
            ["credits_used", "total_credits"],
            as_dict=True,
        )

        credits_used = package.credits_used - row.credits_charged
        credits_remaining = package.total_credits - credits_used

        frappe.db.set_value(
            "Package Purchase",
            row.package_purchase,
            {
                "credits_used": credits_used,
                "credits_remaining": credits_remaining,
                "status": "Active" if credits_remaining > 0 else "Fully Used",
            },
        )
