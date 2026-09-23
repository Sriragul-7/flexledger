import frappe

def class_session_query_conditions(user=None):
    
    user = user or frappe.session.user

    if "FIT Trainer" not in frappe.get_roles(user):
        return ""

    trainer = frappe.db.get_value(
        "Trainer", {"user": user}, "name")

    if not trainer:
        return "`tabClass Session`.`trainer` = ''"

    escaped_trainer = frappe.db.escape(trainer)
    trainer_condition = f"`tabClass Session`.`trainer` = {escaped_trainer}"

    return trainer_condition