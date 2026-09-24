import frappe


def send_low_balance_email(member, package_name, credits_remaining):

    email = frappe.db.get_value("Member", member, "email")
    if not email:
        return

    frappe.sendmail(
        recipients=email,
        subject="Low balance alert",
        message=f"Your package {package_name} has {credits_remaining} credits remaining.",
    )
 