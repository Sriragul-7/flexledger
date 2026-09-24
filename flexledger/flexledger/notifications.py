import frappe

def send_low_balance_email(member, package_name, credits_remaining):
    member_data = frappe.db.get_value("Member", member, ["member_name", "email"], as_dict=True)
    if not member_data or not member_data.email:
        return
    frappe.sendmail(
        recipients=[member_data.email],
        subject="Low Package Balance",
        message=f"Your package {package_name} has {credits_remaining} credits remaining.",
    )
