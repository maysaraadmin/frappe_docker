import frappe
from frappe.model.document import Document

class MembershipType(Document):
    def validate(self):
        self.validate_unique_name()
        self.validate_billing_cycle()
        self.set_default_reminders()
        
    def validate_unique_name(self):
        if self.membership_name:
            existing = frappe.db.exists("Membership Type", {
                "membership_name": self.membership_name, 
                "name": ["!=", self.name]
            })
            if existing:
                frappe.throw("Membership Type with this name already exists")
    
    def validate_billing_cycle(self):
        if self.annual_fee <= 0:
            frappe.throw("Annual Fee must be greater than 0")
    
    def set_default_reminders(self):
        if not self.renewal_reminder_days and self.get("__islocal"):
            # Set default reminder days
            self.append("renewal_reminder_days", {"days_before": 30})
            self.append("renewal_reminder_days", {"days_before": 15})
            self.append("renewal_reminder_days", {"days_before": 7})
    
    def before_save(self):
        self.set_system_fields()
    
    def set_system_fields(self):
        self.created_by = frappe.session.user
        self.modified_by = frappe.session.user
    
    def get_billing_frequency(self):
        """Return billing frequency in months"""
        cycle_map = {
            "Monthly": 1,
            "Quarterly": 3,
            "Semi-Annual": 6,
            "Annual": 12
        }
        return cycle_map.get(self.billing_cycle, 12)
    
    def calculate_prorated_amount(self, days_in_year=365):
        """Calculate prorated amount for partial year"""
        return (self.annual_fee / days_in_year) * days_in_year
    
    def get_facility_access_list(self):
        """Return list of facilities this membership type can access"""
        return [row.facility for row in self.facility_access]

@frappe.whitelist()
def get_membership_tiers():
    return frappe.db.get_all("Membership Type", 
        filters={"is_active": 1},
        fields=["name", "membership_name", "membership_tier", "annual_fee"],
        order_by="annual_fee asc"
    )

@frappe.whitelist()
def get_membership_privileges(membership_type):
    doc = frappe.get_doc("Membership Type", membership_type)
    return {
        "facility_access": [row.facility for row in doc.facility_access],
        "event_discount": doc.event_discount,
        "f_and_b_discount": doc.f_and_b_discount,
        "credit_limit": doc.credit_limit
    }
