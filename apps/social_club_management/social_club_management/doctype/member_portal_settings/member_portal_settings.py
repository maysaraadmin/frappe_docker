import frappe
from frappe.model.document import Document

class MemberPortalSettings(Document):
    def validate(self):
        self.validate_portal_url()
        self.validate_payment_settings()
        
    def validate_portal_url(self):
        if self.portal_url and not self.portal_url.startswith(('http://', 'https://')):
            frappe.throw("Portal URL must start with http:// or https://")
    
    def validate_payment_settings(self):
        if self.enable_member_account_charging and not self.default_credit_limit:
            frappe.throw("Default Credit Limit is required when Member Account Charging is enabled")
    
    def before_save(self):
        self.set_system_fields()
    
    def set_system_fields(self):
        self.created_by = frappe.session.user
        self.modified_by = frappe.session.user
    
    def get_portal_config(self):
        """Get portal configuration for frontend"""
        return {
            "enabled": self.enable_member_portal,
            "url": self.portal_url,
            "online_registration": self.allow_online_registration,
            "email_verification": self.require_email_verification,
            "mobile_verification": self.require_mobile_verification,
            "max_bookings_per_day": self.max_bookings_per_day or 3,
            "max_event_registrations": self.max_event_registrations or 10,
            "payment_gateway": self.payment_gateway,
            "member_account_charging": self.enable_member_account_charging,
            "referral_program": self.enable_referral_program
        }
    
    def send_notification(self, notification_type, recipient, data):
        """Send notification based on type and settings"""
        if notification_type == "booking_confirmation" and self.booking_confirmation_email:
            self.send_booking_confirmation_email(recipient, data)
        elif notification_type == "event_confirmation" and self.event_confirmation_email:
            self.send_event_confirmation_email(recipient, data)
        elif notification_type == "membership_expiry" and self.membership_expiry_reminder:
            self.send_membership_expiry_email(recipient, data)
        elif notification_type == "payment_reminder" and self.payment_reminder:
            self.send_payment_reminder_email(recipient, data)
    
    def send_booking_confirmation_email(self, member, booking_data):
        """Send booking confirmation email"""
        member_doc = frappe.get_doc("Club Member", member)
        
        subject = f"Booking Confirmation - {booking_data.get('facility_name')}"
        message = f"""
        Dear {member_doc.full_name},
        
        Your facility booking has been confirmed:
        
        Facility: {booking_data.get('facility_name')}
        Date: {booking_data.get('booking_date')}
        Time: {booking_data.get('start_time')} to {booking_data.get('end_time')}
        Duration: {booking_data.get('duration_hours')} hours
        Total Amount: AED {booking_data.get('grand_total')}
        
        Please arrive 10 minutes before your scheduled time.
        
        Best regards,
        Social Club Management Team
        """
        
        frappe.sendmail(
            recipients=[member_doc.email],
            subject=subject,
            message=message
        )
    
    def send_event_confirmation_email(self, member, event_data):
        """Send event confirmation email"""
        member_doc = frappe.get_doc("Club Member", member)
        
        subject = f"Event Registration Confirmation - {event_data.get('event_name')}"
        message = f"""
        Dear {member_doc.full_name},
        
        Your registration for the following event has been confirmed:
        
        Event: {event_data.get('event_name')}
        Date: {event_data.get('event_date')}
        Time: {event_data.get('event_time')}
        Venue: {event_data.get('venue')}
        Ticket Number: {event_data.get('ticket_number')}
        
        Please present your ticket at the event entrance.
        
        Best regards,
        Social Club Management Team
        """
        
        frappe.sendmail(
            recipients=[member_doc.email],
            subject=subject,
            message=message
        )
    
    def send_membership_expiry_email(self, member, expiry_data):
        """Send membership expiry reminder email"""
        member_doc = frappe.get_doc("Club Member", member)
        
        days_until_expiry = expiry_data.get('days_until_expiry')
        urgency = "URGENT: " if days_until_expiry <= 7 else ""
        
        subject = f"{urgency}Membership Expiry Reminder - {member_doc.full_name}"
        message = f"""
        Dear {member_doc.full_name},
        
        Your membership is expiring in {days_until_expiry} days on {expiry_data.get('expiry_date')}.
        
        To continue enjoying club facilities and benefits, please renew your membership soon.
        
        Current Membership Tier: {member_doc.membership_tier}
        Renewal Fee: AED {expiry_data.get('renewal_fee')}
        
        You can renew online through the member portal or visit the club reception.
        
        Best regards,
        Social Club Management Team
        """
        
        frappe.sendmail(
            recipients=[member_doc.email],
            subject=subject,
            message=message
        )
    
    def send_payment_reminder_email(self, member, payment_data):
        """Send payment reminder email"""
        member_doc = frappe.get_doc("Club Member", member)
        
        subject = f"Payment Reminder - Invoice {payment_data.get('invoice_number')}"
        message = f"""
        Dear {member_doc.full_name},
        
        This is a reminder that you have an outstanding payment:
        
        Invoice Number: {payment_data.get('invoice_number')}
        Invoice Date: {payment_data.get('invoice_date')}
        Due Date: {payment_data.get('due_date')}
        Amount Due: AED {payment_data.get('amount_due')}
        
        Please make the payment at your earliest convenience to avoid service interruption.
        
        Payment Methods:
        - Online through member portal
        - At club reception
        - Bank transfer
        
        Best regards,
        Social Club Management Team
        """
        
        frappe.sendmail(
            recipients=[member_doc.email],
            subject=subject,
            message=message
        )

@frappe.whitelist()
def get_portal_config():
    """Get portal configuration for frontend"""
    settings = frappe.get_single("Member Portal Settings")
    if not settings:
        return {"error": "Member Portal Settings not configured"}
    
    return settings.get_portal_config()

@frappe.whitelist()
def send_portal_notification(notification_type, recipient, data):
    """Send portal notification"""
    settings = frappe.get_single("Member Portal Settings")
    if not settings:
        return {"error": "Member Portal Settings not configured"}
    
    try:
        settings.send_notification(notification_type, recipient, data)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
