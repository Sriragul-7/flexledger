app_name = "flexledger"
app_title = "FlexLedger"
app_publisher = "SriRagul"
app_description = "Assessment"
app_email = "sriragul.aa@gmail.com"
app_license = "mit"


fixtures = [
	{"dt": "Role", "filters": [["name", "in", ["FIT Front Desk", "FIT Trainer", "FIT Studio Manager"]]]},
]


permission_query_conditions = {"Class Session": "flexledger.permission.class_session_query_conditions"}


after_install = "flexledger.install.after_install"

doc_events = {
	"*": {
		"on_update": "flexledger.audit.log_change",
		"on_submit": "flexledger.audit.log_change",
		"on_cancel": "flexledger.audit.log_change",
	}
}

scheduler_events = {"daily": ["flexledger.api.check_expiring_packages"]}

jinja = {
	"methods": [
		"flexledger.api.get_studio_name",
		"frappe.utils.formatters.format_value",
	]
}
