import frappe

def after_install():

    default_sessions = [
        ("1:1 Personal Training", 2),
        ("Group HIIT", 1),
        ("Yoga Flow", 1),
    ]

    for name, credits in default_sessions:
        
        if not frappe.db.exists("Session Type", name):
           
            doc= frappe.get_doc({
                "doctype": "Session Type",
                "session_type_name": name,
                "credits_required": credits,
                "duration_minutes": 60,
            })
            doc.insert(ignore_permissions=True)

    if not frappe.db.exists("Studio Settings", "Studio Settings"):
        
        user =frappe.session.user if frappe.session.user != "Guest" else ""
        
        doc = frappe.get_doc({
            "doctype": "Studio Settings",
            "studio_name": "Momentum Fitness Studio",
            "manager_email": user,
            "default_cancellation_window_hours": 24,
            "no_show_forfeits_credit": 1,
            "low_balance_alert_threshold": 2,
        })
        doc.insert(ignore_permissions=True)

    frappe.db.commit()
    frappe.msgprint("FlexLedger installed successfully")
