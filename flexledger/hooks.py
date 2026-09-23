app_name = "flexledger"
app_title = "FlexLedger"
app_publisher = "SriRagul"
app_description = "Assessment"
app_email = "sriragul.aa@gmail.com"
app_license = "mit"


fixtures = [
    {"dt": "Role", "filters": [["name", "in", ["FIT Front Desk", "FIT Trainer", "FIT Studio Manager"]]]},
    {"dt": "Custom DocPerm", "filters": [["role", "in", ["FIT Front Desk", "FIT Trainer", "FIT Studio Manager"]]]}
]



permission_query_conditions = {
    "Class Session": "flexledger.permissions.class_session_query_conditions"
}



