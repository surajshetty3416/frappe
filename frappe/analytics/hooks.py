# Where Studio mounts this layer. Without slashes, so paths build as f"/{insights_path}".
insights_path = "studio/analytics"


# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/frappe/analytics/css/insights.css"

# a desk page with an island needs the app's mount path to build links
extend_bootinfo = "frappe.analytics.desk.boot_app_path"

# include js, css files in header of web template
# web_include_css = "/assets/frappe/analytics/css/insights.css"
# web_include_js = "/assets/frappe/analytics/js/insights.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "insights/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "frappe.analytics.utils.jinja_methods",
# 	"filters": "frappe.analytics.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "insights.install.before_install"
after_install = "frappe.analytics.migrate.after_migrate"
after_migrate = "frappe.analytics.migrate.after_migrate"
after_app_install = "frappe.analytics.migrate.after_app_install"

after_request = ["frappe.analytics.doctype.insights_data_source_v3.insights_data_source_v3.after_request"]

fixtures = [
    {
        "dt": "Insights Data Source v3",
        "filters": {"name": "Site DB"},
    },
]

# Uninstallation
# ------------

# before_uninstall = "insights.uninstall.before_uninstall"
# after_uninstall = "insights.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "insights.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
    "Insights Data Source v3": "frappe.analytics.permissions.get_permission_query_conditions",
    "Insights Table v3": "frappe.analytics.permissions.get_permission_query_conditions",
    "Insights Team": "frappe.analytics.permissions.get_permission_query_conditions",
    "Insights Workbook": "frappe.analytics.permissions.get_permission_query_conditions",
    "Insights Query v3": "frappe.analytics.permissions.get_permission_query_conditions",
    "Insights Chart v3": "frappe.analytics.permissions.get_permission_query_conditions",
    "Insights Dashboard v3": "frappe.analytics.permissions.get_permission_query_conditions",
    "Insights Alert": "frappe.analytics.permissions.get_permission_query_conditions",
    "Insights Folder": "frappe.analytics.permissions.get_permission_query_conditions",
}

has_permission = {
    "Insights Data Source v3": "frappe.analytics.permissions.has_doc_permission",
    "Insights Table v3": "frappe.analytics.permissions.has_doc_permission",
    "Insights Team": "frappe.analytics.permissions.has_doc_permission",
    "Insights Workbook": "frappe.analytics.permissions.has_doc_permission",
    "Insights Query v3": "frappe.analytics.permissions.has_doc_permission",
    "Insights Chart v3": "frappe.analytics.permissions.has_doc_permission",
    "Insights Dashboard v3": "frappe.analytics.permissions.has_doc_permission",
    "Insights Alert": "frappe.analytics.permissions.has_doc_permission",
    "Insights Folder": "frappe.analytics.permissions.has_doc_permission",
}

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "User": {
        "on_change": "frappe.analytics.doctype.insights_team.insights_team.update_admin_team",
    },
    # a desk document that links to Insights content renders through an
    # Insights island — see frappe/analytics/desk.py
    "Dashboard": {
        "onload": "frappe.analytics.desk.claim",
    },
    "Dashboard Chart": {
        "onload": "frappe.analytics.desk.claim",
    },
    "DocShare": {
        "validate": "frappe.analytics.permissions.validate_member_share",
    },
    # child tables of workbook members
    ("Insights Dashboard Chart v3", "Has Role", "Insights Query Variable"): {
        "validate": "frappe.analytics.permissions.refuse_member_row_alone",
        "on_trash": "frappe.analytics.permissions.refuse_member_row_alone",
    },
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    "all": [
        "frappe.analytics.doctype.insights_alert.insights_alert.send_alerts",
        "frappe.analytics.api.data_store.sync_tables",
    ],
    "daily": [
        "frappe.analytics.telemetry_scan.run_site_scan",
    ],
    "weekly": [
        "frappe.analytics.doctype.insights_data_source_v3.data_warehouse.cleanup_data_store",
    ],
    "hourly": [
        "frappe.analytics.api.data_store.update_failed_sync_status",
        "frappe.analytics.doctype.insights_table_import_job.insights_table_import_job.run_scheduled_imports",
    ],
}

default_log_clearing_doctypes = {
    "Insights Query Execution Log": 90,
}

# Testing
# -------

before_tests = "frappe.analytics.tests.utils.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "insights.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "insights.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"insights.auth.validate"
# ]

page_renderer = "frappe.analytics.utils.InsightsPageRenderer"


standard_queries = {
    "Insights Query v3": "frappe.analytics.api.search.search_workbook_items",
    "Insights Chart v3": "frappe.analytics.api.search.search_workbook_items",
    "Insights Dashboard v3": "frappe.analytics.api.search.search_workbook_items",
}

# what the AI layer (flow) can do with Insights
flow_tools = [
    "frappe.analytics.flow_tools.list_dashboards",
    "frappe.analytics.flow_tools.create_dashboard",
]

# what Studio opens beside the chat for an artifact of this layer
studio_artifacts = {
    "Insights Dashboard v3": {
        "label": "Dashboard",
        "route": "/studio/analytics/dashboards/{name}",
        "title_field": "title",
    },
    "Insights Chart v3": {"label": "Chart", "route": "/studio/analytics/charts/{name}", "title_field": "title"},
}
