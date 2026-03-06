import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime, add_hours, flt, cint
from datetime import datetime, timedelta

class FacilityBooking(Document):
    def validate(self):
        self.validate_member_status()
        self.validate_booking_time()
        self.validate_availability()
        self.calculate_pricing()
        self.set_end_datetime()
        
    def validate_member_status(self):
        member = frappe.get_doc("Club Member", self.member)
        if not member.can_book_facility():
            frappe.throw(f"Member {member.full_name} cannot book facilities. Current status: {member.membership_status}")
    
    def validate_booking_time(self):
        if self.booking_datetime <= now_datetime():
            frappe.throw("Booking time cannot be in the past")
        
        # Check booking window
        facility = frappe.get_doc("Facility", self.facility)
        max_window = facility.max_booking_window_days or 7
        if self.booking_datetime > add_hours(now_datetime(), max_window * 24):
            frappe.throw(f"Bookings can only be made {max_window} days in advance")
        
        # Check booking duration
        max_duration = facility.max_booking_duration_hours or 2
        if self.duration_hours > max_duration:
            frappe.throw(f"Maximum booking duration is {max_duration} hours")
    
    def validate_availability(self):
        facility = frappe.get_doc("Facility", self.facility)
        is_available, message = facility.is_available_at_time(
            self.booking_datetime, self.duration_hours
        )
        
        if not is_available:
            frappe.throw(message)
    
    def set_end_datetime(self):
        if self.booking_datetime and self.duration_hours:
            self.end_datetime = get_datetime(self.booking_datetime) + timedelta(hours=self.duration_hours)
    
    def calculate_pricing(self):
        if not self.member or not self.facility or not self.duration_hours:
            return
        
        member = frappe.get_doc("Club Member", self.member)
        facility = frappe.get_doc("Facility", self.facility)
        
        # Get rate based on member tier
        rate = facility.get_rate_for_member(member.membership_tier)
        self.rate_applied = rate
        
        # Calculate total amount
        self.total_amount = rate * self.duration_hours
        
        # Calculate VAT (5% for UAE)
        vat_rate = frappe.db.get_single_value("UAE VAT Settings", "vat_rate") or 5
        self.vat_amount = self.total_amount * (vat_rate / 100)
        self.grand_total = self.total_amount + self.vat_amount
    
    def before_save(self):
        self.set_system_fields()
        self.set_booking_date()
    
    def set_system_fields(self):
        if not self.creation_date:
            self.creation_date = frappe.utils.now()
        self.modified_date = frappe.utils.now()
        self.created_by = frappe.session.user
        self.modified_by = frappe.session.user
    
    def set_booking_date(self):
        if self.booking_datetime:
            self.booking_date = get_datetime(self.booking_datetime).date()
    
    def on_submit(self):
        self.create_sales_invoice()
        self.send_booking_confirmation()
    
    def create_sales_invoice(self):
        if self.grand_total <= 0:
            return
        
        # Create Sales Invoice
        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = self.member
        invoice.due_date = frappe.utils.today()
        invoice.currency = "AED"
        
        # Add item for facility booking
        item_code = frappe.db.get_single_value("Member Portal Settings", "facility_booking_item_code")
        if not item_code:
            item_code = "Facility Booking"  # Default item code
        
        invoice.append("items", {
            "item_code": item_code,
            "item_name": f"Facility Booking - {self.facility}",
            "description": f"Booking for {self.facility} on {self.booking_date} from {self.booking_datetime} to {self.end_datetime}",
            "qty": self.duration_hours,
            "rate": self.rate_applied,
            "amount": self.total_amount
        })
        
        # Set taxes
        vat_rate = frappe.db.get_single_value("UAE VAT Settings", "vat_rate") or 5
        invoice.append("taxes", {
            "charge_type": "On Net Total",
            "account_head": frappe.db.get_single_value("UAE VAT Settings", "vat_account"),
            "rate": vat_rate
        })
        
        invoice.insert()
        invoice.submit()
        
        self.invoice = invoice.name
        frappe.msgprint(f"Sales Invoice {invoice.name} created successfully")
    
    def send_booking_confirmation(self):
        member = frappe.get_doc("Club Member", self.member)
        facility = frappe.get_doc("Facility", self.facility)
        
        # Send email confirmation
        subject = f"Facility Booking Confirmation - {facility.facility_name}"
        message = f"""
        Dear {member.full_name},
        
        Your facility booking has been confirmed:
        
        Facility: {facility.facility_name}
        Date: {self.booking_date}
        Time: {self.booking_datetime} to {self.end_datetime}
        Duration: {self.duration_hours} hours
        Total Amount: AED {self.grand_total}
        
        Please arrive 10 minutes before your scheduled time.
        
        Best regards,
        Social Club Management Team
        """
        
        frappe.sendmail(
            recipients=[member.email],
            subject=subject,
            message=message
        )
        
        # Send SMS confirmation if configured
        self.send_sms_confirmation(member)
    
    def send_sms_confirmation(self, member):
        try:
            sms_gateway = frappe.db.get_single_value("Member Portal Settings", "sms_gateway")
            if not sms_gateway:
                return
            
            message = f"Booking confirmed: {self.facility} on {self.booking_date} at {self.booking_datetime}. Total: AED {self.grand_total}"
            
            # Integration with SMS gateway would go here
            # This is a placeholder for SMS integration
            frappe.enqueue(
                "social_club_management.utils.send_sms",
                recipient=member.mobile_no,
                message=message
            )
        except Exception as e:
            frappe.log_error(f"SMS sending failed: {str(e)}", "Facility Booking SMS")
    
    def cancel_booking(self, reason):
        if self.status == "Cancelled":
            frappe.throw("Booking is already cancelled")
        
        facility = frappe.get_doc("Facility", self.facility)
        cancellation_hours = facility.cancellation_policy_hours or 24
        cancellation_fee_percent = facility.cancellation_fee_percentage or 50
        
        # Calculate cancellation fee
        booking_time = get_datetime(self.booking_datetime)
        current_time = now_datetime()
        hours_until_booking = (booking_time - current_time).total_seconds() / 3600
        
        if hours_until_booking < cancellation_hours:
            # Apply cancellation fee
            self.cancellation_fee = self.grand_total * (cancellation_fee_percent / 100)
            self.refund_amount = self.grand_total - self.cancellation_fee
        else:
            # Full refund
            self.cancellation_fee = 0
            self.refund_amount = self.grand_total
        
        self.status = "Cancelled"
        self.cancellation_reason = reason
        self.save()
        
        # Process refund if applicable
        if self.refund_amount > 0:
            self.process_refund()
        
        # Send cancellation notification
        self.send_cancellation_notification()
    
    def process_refund(self):
        if self.invoice:
            # Create credit note for refund
            credit_note = frappe.new_doc("Sales Invoice")
            credit_note.customer = self.member
            credit_note.is_return = 1
            credit_note.return_against = self.invoice
            credit_note.currency = "AED"
            
            # Add refund item
            item_code = frappe.db.get_single_value("Member Portal Settings", "facility_booking_item_code")
            if not item_code:
                item_code = "Facility Booking"
            
            credit_note.append("items", {
                "item_code": item_code,
                "item_name": f"Refund - Facility Booking Cancellation",
                "qty": -1,
                "rate": self.refund_amount,
                "amount": -self.refund_amount
            })
            
            credit_note.insert()
            credit_note.submit()
            
            frappe.msgprint(f"Credit Note {credit_note.name} created for refund")
    
    def send_cancellation_notification(self):
        member = frappe.get_doc("Club Member", self.member)
        facility = frappe.get_doc("Facility", self.facility)
        
        subject = f"Booking Cancellation - {facility.facility_name}"
        message = f"""
        Dear {member.full_name},
        
        Your facility booking has been cancelled:
        
        Facility: {facility.facility_name}
        Date: {self.booking_date}
        Time: {self.booking_datetime} to {self.end_datetime}
        Cancellation Reason: {self.cancellation_reason}
        Refund Amount: AED {self.refund_amount}
        
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
def create_facility_booking(member, facility, date, time, duration_hours, purpose=""):
    try:
        booking = frappe.new_doc("Facility Booking")
        booking.member = member
        booking.facility = facility
        booking.booking_date = date
        booking.booking_datetime = f"{date} {time}"
        booking.duration_hours = float(duration_hours)
        booking.purpose = purpose
        booking.status = "Confirmed"
        booking.insert()
        booking.submit()
        
        return {"success": True, "booking": booking.name}
    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def cancel_facility_booking(booking, reason):
    try:
        booking_doc = frappe.get_doc("Facility Booking", booking)
        booking_doc.cancel_booking(reason)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def get_member_bookings(member, status=None):
    filters = {"member": member}
    if status:
        filters["status"] = status
    
    return frappe.db.get_all("Facility Booking",
        filters=filters,
        fields=["name", "facility", "booking_date", "booking_datetime", "end_datetime", "duration_hours", "status", "grand_total"],
        order_by="booking_datetime desc"
    )
