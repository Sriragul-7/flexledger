import frappe
from frappe.query_builder import DocType

def get_low_balance_member():

    PP = DocType("Package Purchase")
    
    threshold= frappe.db.get_single_value("Studio Settings", "low_balance_alert_threshold")

    if not threshold:
        frappe.throw("Studio Settings Threshold not set")
    
    res = (frappe.qb.from_(PP)
    .select(PP.name, PP.member, PP.credits_remaining, PP.expiry_date)
    .where((PP.credits_remaining <= threshold) & (PP.status == "Active"))
    .orderby(PP.credits_remaining)
    .run(as_dict=True))

    if not res:
        frappe.throw("Low  Balance Member doesnot exist")

    return res
    
def transfer_package(package_name, new_member):

    try:
        package = frappe.db.get_value("Package Purchase", package_name, ["member", "credits_used", "status"], as_dict = True)     
        
        if not package:
            frappe.throw("Invalid Package")
        if not package.status == "Active":
            frappe.throw("Package is not Active")
        if not frappe.db.exists("Member", new_member):
            frappe.throw("Invalid New Member")
        if package.member == new_member:
            frappe.throw("Can not Transfer for same Mmber")
        frappe.db.sql(
            "UPDATE `tabPackage Purchase` SET member=%s WHERE name=%s",
            (new_member, package_name),
        )
        frappe.db.commit()
        return {"success": True, "package": package_name, "member": new_member}
    except Exception:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Package Transfer Failed")
        raise


@frappe.whitelist()
def unsafe_get_members():

    return frappe.db.get_all("Member", fields=["*"])


@frappe.whitelist()
def safe_get_members():
    
    fields=["name", "member_name", "join_date", "status", "user"]
    if "FIT Studio Manager" in frappe.get_roles(frappe.session.user):
        fields += ["phone","email"]
        
    return (frappe.get_list("Member",fields=fields))
    3333