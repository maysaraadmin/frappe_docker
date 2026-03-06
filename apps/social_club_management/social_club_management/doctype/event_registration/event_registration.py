import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime, add_hours, add_days, flt, cint, random_string
import qrcode
import io
import base64

class EventRegistration(Document):
    def validate(self):
        self.validate_member_status()
        self.validate_event_availability()
        self.calculate_fees()
        self.generate_ticket_number()
        
    def validate_member_status(self):
        member = frappe.get_doc("Club Member", self.member)
        if member.membership_status not in ["Active"]:
            frappe.throw(f"Member {member.full_name} is not active. Current status: {member.membership_status}")
    
    def validate_event_availability(self):
        event = frappe.get_doc("Club Event", self.event)
        can_register, message = event.can_register(self.member)
        if not can_register:
            frappe.throw(message)
        
        # Check if already registered
        existing = frappe.db.exists("Event Registration", {
            "event": self.event,
            "member": self.member,
            "status": ["!=", "Cancelled"]
        })
        if existing:
            frappe.throw("Member is already registered for this event")
    
    def calculate_fees(self):
        if not self.event or not self.member:
            return
        
        event = frappe.get_doc("Club Event", self.event)
        member = frappe.get_doc("Club Member", self.member)
        
        # Calculate member fee
        self.member_fee = event.get_fee_for_member(member.membership_tier)
        
        # Calculate guest fee
        self.guest_fee = event.guest_fee * self.number_of_guests
        
        # Calculate total
        self.total_fee = self.member_fee + self.guest_fee
        
        # Calculate VAT (5% for UAE)
        vat_rate = frappe.db.get_single_value("UAE VAT Settings", "vat_rate") or 5
        self.vat_amount = self.total_fee * (vat_rate / 100)
        self.grand_total = self.total_fee + self.vat_amount
    
    def generate_ticket_number(self):
        if not self.ticket_number:
            # Generate unique ticket number
            event_code = self.event[:3].upper()
            member_code = self.member[:3].upper()
            random_suffix = random_string(6).upper()
            self.ticket_number = f"EVT-{event_code}-{member_code}-{random_suffix}"
    
    def before_save(self):
        self.set_system_fields()
        self.set_waitlist_position()
    
    def set_system_fields(self):
        self.created_by = frappe.session.user
        self.modified_by = frappe.session.user
    
    def set_waitlist_position(self):
        if self.status == "Waitlisted":
            # Calculate waitlist position
            waitlist_count = frappe.db.count("Event Registration", {
                "event": self.event,
                "status": "Waitlisted",
                "registration_date": ["<", self.registration_date]
            })
            self.waitlist_position = waitlist_count + 1
    
    def on_submit(self):
        self.create_sales_invoice()
        self.generate_qr_code()
        self.send_registration_confirmation()
        
        # Update event registration count
        event = frappe.get_doc("Club Event", self.event)
        event.update_registration_count()
        event.save()
    
    def create_sales_invoice(self):
        if self.grand_total <= 0:
            return
        
        # Create Sales Invoice
        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = self.member
        invoice.due_date = frappe.utils.today()
        invoice.currency = "AED"
        
        # Add event registration fee
        item_code = frappe.db.get_single_value("Member Portal Settings", "event_registration_item_code")
        if not item_code:
            item_code = "Event Registration"
        
        event = frappe.get_doc("Club Event", self.event)
        invoice.append("items", {
            "item_code": item_code,
            "item_name": f"Event Registration - {event.event_name}",
            "description": f"Registration for {event.event_name} on {event.start_date}",
            "qty": 1,
            "rate": self.total_fee,
            "amount": self.total_fee
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
    
    def generate_qr_code(self):
        """Generate QR code for event ticket"""
        qr_data = {
            "ticket_number": self.ticket_number,
            "event": self.event,
            "member": self.member,
            "registration_date": self.registration_date
        }
        
        qr_string = str(qr_data)
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_string)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for storage
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        # Save QR code as file
        filename = f"qr_{self.ticket_number}.png"
        file_doc = frappe.new_doc("File")
        file_doc.file_name = filename
        file_doc.content = img_str
        file_doc.attached_to_doctype = self.doctype
        file_doc.attached_to_name = self.name
        file_doc.insert()
        
        self.qr_code = file_doc.file_url
    
    def send_registration_confirmation(self):
        """Send registration confirmation email"""
        member = frappe.get_doc("Club Member", self.member)
        event = frappe.get_doc("Club Event", self.event)
        
        subject = f"Event Registration Confirmation - {event.event_name}"
        message = f"""
        Dear {member.full_name},
        
        Your registration for the following event has been confirmed:
        
        Event: {event.event_name}
        Date: {event.start_date}
        Time: {event.start_time}
        Venue: {event.venue}
        Ticket Number: {self.ticket_number}
        Total Amount: AED {self.grand_total}
        
        {'Guests: ' + str(self.number_of_guests) if self.number_of_guests > 0 else ''}
        
        Please present your ticket at the event entrance.
        
        Best regards,
        Social Club Management Team
        """
        
        frappe.sendmail(
            recipients=[member.email],
            subject=subject,
            message=message,
            attachments=[self.qr_code] if self.qr_code else None
        )
        
        self.ticket_sent = 1
    
    def offer_spot(self):
        """Offer spot to waitlisted member"""
        if self.status != "Waitlisted":
            frappe.throw("Registration is not on waitlist")
        
        self.status = "Registered"
        self.spot_offered_date = frappe.utils.now()
        self.spot_confirmation_deadline = add_hours(self.spot_offered_date, 24)
        self.save()
        
        # Send spot offer notification
        self.send_spot_offer_notification()
        
        # Schedule automatic cancellation if not confirmed
        frappe.enqueue(
            "social_club_management.utils.expire_waitlist_offer",
            registration=self.name,
            execute_at=self.spot_confirmation_deadline
        )
    
    def send_spot_offer_notification(self):
        """Send spot offer notification to member"""
        member = frappe.get_doc("Club Member", self.member)
        event = frappe.get_doc("Club Event", self.event)
        
        subject = f"Spot Available - {event.event_name}"
        message = f"""
        Dear {member.full_name},
        
        Good news! A spot has become available for the following event:
        
        Event: {event.event_name}
        Date: {event.start_date}
        Time: {event.start_time}
        Venue: {event.venue}
        
        Please confirm your registration within 24 hours by clicking the link below:
        
        [Confirm Registration Link]
        
        If you don't confirm within 24 hours, the spot will be offered to the next person on the waitlist.
        
        Best regards,
        Social Club Management Team
        """
        
        frappe.sendmail(
            recipients=[member.email],
            subject=subject,
            message=message
        )
    
    def confirm_spot(self):
        """Confirm spot after waitlist offer"""
        if self.status != "Registered" or not self.spot_offered_date:
            frappe.throw("No spot has been offered for confirmation")
        
        if frappe.utils.now() > self.spot_confirmation_deadline:
            frappe.throw("Confirmation deadline has passed")
        
        self.status = "Confirmed"
        self.save()
        
        # Process payment if required
        if self.grand_total > 0 and self.payment_status != "Paid":
            self.process_payment()
        
        # Generate ticket
        self.generate_qr_code()
        self.ticket_sent = 0
        self.send_registration_confirmation()
    
    def cancel_registration(self, reason):
        """Cancel event registration"""
        if self.status == "Cancelled":
            frappe.throw("Registration is already cancelled")
        
        self.status = "Cancelled"
        self.cancellation_reason = reason
        self.save()
        
        # Process refund if applicable
        if self.payment_status == "Paid":
            self.process_refund()
        
        # Update event registration count
        event = frappe.get_doc("Club Event", self.event)
        event.update_registration_count()
        event.save()
        
        # Process waitlist if this was a confirmed registration
        if self.status in ["Registered", "Confirmed"]:
            event.process_waitlist()
        
        # Send cancellation notification
        self.send_cancellation_notification()
    
    def process_refund(self):
        """Process refund for cancelled registration"""
        if not self.invoice:
            return
        
        # Create credit note for refund
        credit_note = frappe.new_doc("Sales Invoice")
        credit_note.customer = self.member
        credit_note.is_return = 1
        credit_note.return_against = self.invoice
        credit_note.currency = "AED"
        
        item_code = frappe.db.get_single_value("Member Portal Settings", "event_registration_item_code")
        if not item_code:
            item_code = "Event Registration"
        
        credit_note.append("items", {
            "item_code": item_code,
            "item_name": f"Refund - Event Registration Cancellation",
            "qty": -1,
            "rate": self.grand_total,
            "amount": -self.grand_total
        })
        
        credit_note.insert()
        credit_note.submit()
        
        self.refund_amount = self.grand_total
        self.payment_status = "Refunded"
        self.save()
        
        frappe.msgprint(f"Credit Note {credit_note.name} created for refund")
    
    def send_cancellation_notification(self):
        """Send cancellation notification"""
        member = frappe.get_doc("Club Member", self.member)
        event = frappe.get_doc("Club Event", self.event)
        
        subject = f"Registration Cancelled - {event.event_name}"
        message = f"""
        Dear {member.full_name},
        
        Your registration for the following event has been cancelled:
        
        Event: {event.event_name}
        Date: {event.start_date}
        Time: {event.start_time}
        Cancellation Reason: {self.cancellation_reason}
        Refund Amount: AED {self.refund_amount or 0}
        
        We apologize for any inconvenience.
        
        Best regards,
        Social Club Management Team
        """
        
        frappe.sendmail(
            recipients=[member.email],
            subject=subject,
            message=message
        )
    
    def check_in(self):
        """Check in member at event"""
        if self.status != "Confirmed":
            frappe.throw("Registration is not confirmed")
        
        # Validate QR code if available
        if self.qr_code:
            # QR code validation logic would go here
            pass
        
        self.status = "Checked-In"
        self.save()
        
        return True

@frappe.whitelist()
def confirm_waitlist_spot(registration):
    try:
        reg_doc = frappe.get_doc("Event Registration", registration)
        reg_doc.confirm_spot()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def cancel_event_registration(registration, reason):
    try:
        reg_doc = frappe.get_doc("Event Registration", registration)
        reg_doc.cancel_registration(reason)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def check_in_member(registration, qr_data=None):
    try:
        reg_doc = frappe.get_doc("Event Registration", registration)
        success = reg_doc.check_in()
        return {"success": success, "member": reg_doc.member}
    except Exception as e:
        return {"success": False, "error": str(e)}
