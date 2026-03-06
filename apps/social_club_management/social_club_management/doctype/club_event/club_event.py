import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime, flt, cint
from datetime import datetime, timedelta

class ClubEvent(Document):
    def validate(self):
        self.validate_event_dates()
        self.validate_capacity()
        self.validate_pricing()
        self.update_registration_count()
        
    def validate_event_dates(self):
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                frappe.throw("Start date cannot be after end date")
        
        if self.start_date == self.end_date and self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                frappe.throw("Start time must be before end time")
        
        # Check if event is in the past
        event_datetime = get_datetime(f"{self.start_date} {self.start_time or '00:00:00'}")
        if event_datetime < now_datetime() and self.event_status not in ["Completed", "Cancelled"]:
            frappe.throw("Event dates cannot be in the past")
    
    def validate_capacity(self):
        if self.max_capacity <= 0:
            frappe.throw("Maximum capacity must be greater than 0")
    
    def validate_pricing(self):
        if any(fee < 0 for fee in [self.member_fee, self.non_member_fee, self.vip_fee, self.guest_fee]):
            frappe.throw("Fees cannot be negative")
    
    def update_registration_count(self):
        """Update current registration count"""
        count = frappe.db.count("Event Registration", {
            "event": self.name,
            "status": ["!=", "Cancelled"]
        })
        self.current_registrations = count
        self.available_spots = self.max_capacity - count
        
        # Update event status based on availability
        if self.available_spots <= 0 and self.event_status not in ["Full", "Cancelled", "Completed"]:
            self.event_status = "Full"
        elif self.available_spots > 0 and self.event_status == "Full":
            self.event_status = "Published"
    
    def before_save(self):
        self.set_system_fields()
        self.update_event_status()
    
    def set_system_fields(self):
        self.created_by = frappe.session.user
        self.modified_by = frappe.session.user
    
    def update_event_status(self):
        if self.is_published and self.event_status == "Draft":
            self.event_status = "Published"
        elif not self.is_published and self.event_status == "Published":
            self.event_status = "Draft"
    
    def can_register(self, member=None):
        """Check if member can register for this event"""
        # Check if event is published
        if self.event_status not in ["Published", "Full"]:
            return False, "Event is not open for registration"
        
        # Check registration deadline
        if self.registration_deadline:
            deadline = get_datetime(self.registration_deadline)
            if deadline < now_datetime():
                return False, "Registration deadline has passed"
        
        # Check if event is full
        if self.available_spots <= 0:
            if self.enable_waitlist:
                return True, "Event is full, you will be added to waitlist"
            else:
                return False, "Event is full"
        
        return True, "Registration available"
    
    def get_fee_for_member(self, member_tier):
        """Get fee based on member tier"""
        if member_tier == "VIP":
            return self.vip_fee or self.member_fee
        return self.member_fee
    
    def register_member(self, member, number_of_guests=0):
        """Register a member for the event"""
        can_register, message = self.can_register(member)
        if not can_register:
            frappe.throw(message)
        
        # Check if member is already registered
        existing = frappe.db.exists("Event Registration", {
            "event": self.name,
            "member": member,
            "status": ["!=", "Cancelled"]
        })
        if existing:
            frappe.throw("Member is already registered for this event")
        
        # Create registration
        registration = frappe.new_doc("Event Registration")
        registration.event = self.name
        registration.member = member
        registration.number_of_guests = number_of_guests
        registration.registration_date = frappe.utils.today()
        registration.registration_time = frappe.utils.now()
        
        # Calculate fees
        member_doc = frappe.get_doc("Club Member", member)
        member_fee = self.get_fee_for_member(member_doc.membership_tier)
        guest_fee = self.guest_fee * number_of_guests
        total_fee = member_fee + guest_fee
        
        registration.member_fee = member_fee
        registration.guest_fee = guest_fee
        registration.total_fee = total_fee
        
        # Set status
        if self.available_spots > 0:
            registration.status = "Registered"
        else:
            registration.status = "Waitlisted"
        
        registration.insert()
        
        # Update registration count
        self.update_registration_count()
        self.save()
        
        # Send confirmation
        registration.send_registration_confirmation()
        
        return registration.name
    
    def get_attendee_list(self):
        """Get list of confirmed attendees"""
        return frappe.db.get_all("Event Registration",
            filters={
                "event": self.name,
                "status": "Registered"
            },
            fields=["member", "number_of_guests", "registration_date", "total_fee"],
            order_by="registration_date asc"
        )
    
    def get_waitlist(self):
        """Get waitlist"""
        return frappe.db.get_all("Event Registration",
            filters={
                "event": self.name,
                "status": "Waitlisted"
            },
            fields=["member", "registration_date"],
            order_by="registration_date asc"
        )
    
    def process_waitlist(self):
        """Process waitlist when spots become available"""
        if self.available_spots <= 0:
            return
        
        waitlist = self.get_waitlist()
        spots_available = self.available_spots
        
        for i, registration in enumerate(waitlist):
            if i >= spots_available:
                break
            
            # Offer spot to waitlisted member
            reg_doc = frappe.get_doc("Event Registration", registration.name)
            reg_doc.offer_spot()
    
    def cancel_event(self, reason):
        """Cancel the entire event"""
        if self.event_status == "Cancelled":
            frappe.throw("Event is already cancelled")
        
        self.event_status = "Cancelled"
        self.save()
        
        # Cancel all registrations and process refunds
        registrations = frappe.db.get_all("Event Registration",
            filters={"event": self.name, "status": ["!=", "Cancelled"]},
            fields=["name"]
        )
        
        for reg in registrations:
            reg_doc = frappe.get_doc("Event Registration", reg.name)
            reg_doc.cancel_registration(reason)
        
        # Send event cancellation notification
        self.send_event_cancellation_notification(reason)
    
    def send_event_cancellation_notification(self, reason):
        """Send cancellation notification to all registered members"""
        registrations = frappe.db.get_all("Event Registration",
            filters={"event": self.name, "status": ["!=", "Cancelled"]},
            fields=["member"]
        )
        
        for reg in registrations:
            member = frappe.get_doc("Club Member", reg.member)
            
            subject = f"Event Cancelled - {self.event_name}"
            message = f"""
            Dear {member.full_name},
            
            The following event has been cancelled:
            
            Event: {self.event_name}
            Date: {self.start_date}
            Time: {self.start_time}
            Venue: {self.venue}
            
            Cancellation Reason: {reason}
            
            Any fees paid will be refunded to your account.
            
            We apologize for any inconvenience.
            
            Best regards,
            Social Club Management Team
            """
            
            frappe.sendmail(
                recipients=[member.email],
                subject=subject,
                message=message
            )

@frappe.whitelist()
def get_upcoming_events():
    return frappe.db.get_all("Club Event",
        filters={
            "event_status": ["in", ["Published", "Full"]],
            "start_date": [">=", frappe.utils.today()]
        },
        fields=["name", "event_name", "event_type", "start_date", "start_time", "venue", "member_fee", "available_spots"],
        order_by="start_date asc"
    )

@frappe.whitelist()
def register_for_event(event, member, number_of_guests=0):
    try:
        event_doc = frappe.get_doc("Club Event", event)
        registration_name = event_doc.register_member(member, int(number_of_guests))
        return {"success": True, "registration": registration_name}
    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def get_event_details(event):
    event_doc = frappe.get_doc("Club Event", event)
    return event_doc.as_dict()
