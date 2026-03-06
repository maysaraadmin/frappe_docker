import frappe
from frappe.model.document import Document
from frappe.utils import today, add_days, add_years, validate_email, cint, flt
import re

class ClubMember(Document):
    def validate(self):
        self.validate_email()
        self.validate_mobile_number()
        self.validate_member_id()
        self.set_expiry_date()
        self.set_full_name()
        self.validate_family_account()
        
    def validate_email(self):
        if self.email and not validate_email(self.email):
            frappe.throw("Invalid email address")
            
        # Check for unique email
        if self.email:
            existing = frappe.db.exists("Club Member", {"email": self.email, "name": ["!=", self.name]})
            if existing:
                frappe.throw("Email address already exists")
    
    def validate_mobile_number(self):
        if self.mobile_no:
            # UAE mobile format validation: +971-XX-XXX-XXXX or 05X-XXX-XXXX
            uae_pattern = r'^(\+971-5[0-9]-[0-9]{3}-[0-9]{4}|05[0-9]-[0-9]{3}-[0-9]{4})$'
            if not re.match(uae_pattern, self.mobile_no):
                frappe.throw("Mobile number must be in UAE format: +971-XX-XXX-XXXX or 05X-XXX-XXXX")
    
    def validate_member_id(self):
        if self.member_id:
            existing = frappe.db.exists("Club Member", {"member_id": self.member_id, "name": ["!=", self.name]})
            if existing:
                frappe.throw("Member ID already exists")
    
    def set_expiry_date(self):
        if not self.expiry_date and self.join_date:
            # Set expiry to 1 year from join date by default
            self.expiry_date = add_years(self.join_date, 1)
    
    def set_full_name(self):
        if self.first_name and self.last_name:
            self.full_name = f"{self.first_name} {self.middle_name or ''} {self.last_name}".strip()
    
    def validate_family_account(self):
        if self.family_account and self.family_account == self.name:
            frappe.throw("Family Account cannot be the same as current member")
        
        # If this is a primary member, ensure family account points to self
        if self.primary_member and self.family_account != self.name:
            self.family_account = self.name
    
    def before_save(self):
        self.set_system_fields()
        self.update_membership_status()
    
    def set_system_fields(self):
        if not self.creation_date:
            self.creation_date = frappe.utils.now()
        self.modified_date = frappe.utils.now()
        self.created_by = frappe.session.user
        self.modified_by = frappe.session.user
    
    def update_membership_status(self):
        if self.expiry_date and self.expiry_date < today():
            if self.membership_status == "Active":
                self.membership_status = "Expired"
                frappe.msgprint(f"Membership for {self.full_name} has expired")
    
    def on_update(self):
        self.update_family_members()
        self.check_referral_bonus()
    
    def update_family_members(self):
        if self.primary_member and self.family_account == self.name:
            # Update all family members to point to this primary member
            frappe.db.sql("""
                UPDATE `tabClub Member` 
                SET family_account = %s 
                WHERE family_account = %s AND name != %s
            """, (self.name, self.name, self.name))
    
    def check_referral_bonus(self):
        if self.referral_member and self.membership_status == "Active":
            # Check if this is a new activation and award referral bonus
            referral_doc = frappe.get_doc("Club Member", self.referral_member)
            if not frappe.db.exists("Referral Bonus", {"new_member": self.name}):
                self.create_referral_bonus(referral_doc)
    
    def create_referral_bonus(self, referrer):
        bonus_amount = frappe.db.get_single_value("Member Portal Settings", "referral_bonus_amount") or 100
        
        # Create referral bonus record
        bonus = frappe.new_doc("Referral Bonus")
        bonus.referrer = referrer.name
        bonus.new_member = self.name
        bonus.bonus_amount = bonus_amount
        bonus.bonus_date = today()
        bonus.status = "Credited"
        bonus.insert()
        
        # Update referrer's account balance
        frappe.db.set_value("Club Member", referrer.name, "referral_bonus", 
            flt(referrer.referral_bonus) + flt(bonus_amount))
        
        frappe.msgprint(f"Referral bonus of AED {bonus_amount} credited to {referrer.full_name}")
    
    def can_book_facility(self):
        return self.membership_status in ["Active"]
    
    def can_charge_to_account(self):
        if self.membership_status != "Active":
            return False
        
        credit_limit = flt(self.credit_limit)
        account_balance = flt(self.account_balance)
        
        return account_balance <= credit_limit

@frappe.whitelist()
def get_member_details(member_id):
    member = frappe.get_doc("Club Member", member_id)
    return member.as_dict()

@frappe.whitelist()
def validate_member_email(email, member_name=None):
    if not validate_email(email):
        return {"valid": False, "message": "Invalid email address"}
    
    existing = frappe.db.exists("Club Member", {"email": email, "name": ["!=", member_name] if member_name else None})
    if existing:
        return {"valid": False, "message": "Email address already exists"}
    
    return {"valid": True, "message": "Email available"}

@frappe.whitelist()
def get_family_members(primary_member):
    return frappe.db.get_all("Club Member", 
        filters={"family_account": primary_member, "name": ["!=", primary_member]},
        fields=["name", "full_name", "email", "mobile_no", "membership_status"]
    )
