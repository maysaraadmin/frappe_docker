app_name = "social_club_management"
app_title = "Social Club Management"
app_publisher = "Maysara Mohamed"
app_description = "Social Club Management System for UAE"
app_icon = "octicon octicon-organization"
app_color = "grey"
app_email = "maysara.mubarak.mohamed@gmail.com"
app_license = "gpl-3.0"

# Includes in JS bundles
# include_js = "/assets/social_club_management/js/social_club_management.min.js"

# Include in build.json
# include_in_build_json = True

# Home Pages
# app_home = "/social_club_management"

# DocTypes
doctype_list = [
    "Club Member",
    "Membership Type", 
    "Membership Renewal",
    "Family Member",
    "Facility",
    "Facility Booking",
    "Facility Type",
    "Club Event",
    "Event Registration",
    "Event Ticket",
    "POS Member Charge",
    "UAE VAT Settings",
    "WPS File",
    "End of Service Calculation",
    "Member Portal Settings"
]

# Custom Reports
report_list = [
    "Membership Renewal Forecast",
    "Facility Utilization Report",
    "Event Attendance Report",
    "F&B Sales Report",
    "VAT 201 Return",
    "Payroll Register"
]

# Page Routes
# page_routes = [
#     {"path": "social-club-member", "page": "social_club_management/pages/social_club_member.html"},
# ]

# Website Routes
# website_route_rules = [
#     {"from_route": "/member/<path:member_id>", "to_route": "member-profile"},
# ]

# Permissions
# permission_query_conditions = {
#     "Club Member": "user.name == doc.owner or 'System Manager' in frappe.get_roles()",
# }

# DocType Class Overrides
# override_doctype_class = {
#     "Customer": "social_club_management.overrides.customer",
# }

# Standard Queries
# standard_queries = {
#     "Customer": "social_club_management.queries.get_customer_list"
# }

# Boot Scripts
# boot_session = [
#     "social_club_management.boot.session"
# ]

# Scheduler Events
# scheduler_events = {
#     "daily": [
#         "social_club_management.tasks.send_membership_expiry_reminders",
#         "social_club_management.tasks.generate_recurring_invoices"
#     ],
#     "weekly": [
#         "social_club_management.tasks.weekly_reports"
#     ]
# }

# Email Templates
# email_templates = {
#     "membership_expiry": {
#         "subject": "Membership Expiry Reminder",
#         "response": "social_club_management/templates/emails/membership_expiry.html"
#     }
# }

# Workflow States
# workflow_states = {
#     "Facility Booking": ["Pending", "Confirmed", "Cancelled"],
#     "Event Registration": ["Registered", "Confirmed", "Cancelled"]
# }

# Data Migration
# data_migration = {
#     "migrate_from_legacy": "social_club_management.migration.legacy_system"
# }

# API Whitelist
# api_whitelisted_methods = {
#     "social_club_management.api.get_member_details": "get_member_details",
#     "social_club_management.api.book_facility": "book_facility"
# }

# Custom Fields
# custom_fields = {
#     "Customer": [
#         {
#             "fieldname": "membership_id",
#             "label": "Membership ID",
#             "fieldtype": "Data",
#             "insert_after": "customer_name"
#         }
#     ]
# }

# Standard Search
# standard_search = {
#     "Club Member": ["member_name", "email", "phone"],
#     "Facility": ["facility_name", "facility_type"]
# }

# Notification Settings
# notification_config = {
#     "for_doctype": {
#         "Club Member": {
#             "enabled": True,
#             "recipients": ["Membership Coordinator"],
#             "sender": "System Manager",
#             "subject": "New Member Registration",
#             "template": "new_member_registration"
#         }
#     }
# }
