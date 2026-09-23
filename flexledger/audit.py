import frappe


def log_change(doc, method=None):

    if doc.doctype == "Audit Logs":
        return

    action = method or "on_update"

    frappe.get_doc({
        "doctype": "Audit Logs",
        "doctype_name": doc.doctype,
        "document_name": doc.name,
        "action": action,
        "user": frappe.session.user,
        "timestamp": frappe.utils.now_datetime(),
    }).insert(ignore_permissions=True)
