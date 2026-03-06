import frappe
import requests
import json
from frappe.utils import now_datetime

def send_sms(recipient, message, gateway_url=None, api_key=None, sender_id=None):
    """Send SMS using configured gateway"""
    try:
        # Get settings if not provided
        if not gateway_url:
            gateway_url = frappe.db.get_single_value("Member Portal Settings", "sms_gateway")
        if not api_key:
            api_key = frappe.db.get_single_value("Member Portal Settings", "sms_api_key")
        if not sender_id:
            sender_id = frappe.db.get_single_value("Member Portal Settings", "sms_sender_id")
        
        if not gateway_url or not api_key:
            frappe.log_error("SMS Gateway not configured", "SMS Sending Failed")
            return False
        
        # Prepare request based on gateway type
        if "telr" in gateway_url.lower():
            return send_telr_sms(recipient, message, gateway_url, api_key, sender_id)
        elif "network" in gateway_url.lower():
            return send_network_sms(recipient, message, gateway_url, api_key, sender_id)
        else:
            # Generic SMS API
            return send_generic_sms(recipient, message, gateway_url, api_key, sender_id)
    
    except Exception as e:
        frappe.log_error(f"SMS sending failed: {str(e)}", "SMS Error")
        return False

def send_telr_sms(recipient, message, gateway_url, api_key, sender_id):
    """Send SMS via Telr gateway"""
    payload = {
        "api_key": api_key,
        "sender_id": sender_id,
        "recipient": recipient,
        "message": message
    }
    
    response = requests.post(gateway_url, json=payload, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        if result.get("status") == "success":
            log_sms_message(recipient, message, "Sent", result.get("message_id"))
            return True
    
    log_sms_message(recipient, message, "Failed", None, str(response.text))
    return False

def send_network_sms(recipient, message, gateway_url, api_key, sender_id):
    """Send SMS via Network International gateway"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "from": sender_id,
        "to": recipient,
        "body": message
    }
    
    response = requests.post(gateway_url, json=payload, headers=headers, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        if result.get("status") == "sent":
            log_sms_message(recipient, message, "Sent", result.get("sid"))
            return True
    
    log_sms_message(recipient, message, "Failed", None, str(response.text))
    return False

def send_generic_sms(recipient, message, gateway_url, api_key, sender_id):
    """Send SMS via generic gateway"""
    payload = {
        "api_key": api_key,
        "sender": sender_id,
        "to": recipient,
        "message": message
    }
    
    response = requests.post(gateway_url, data=payload, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            log_sms_message(recipient, message, "Sent", result.get("message_id"))
            return True
    
    log_sms_message(recipient, message, "Failed", None, str(response.text))
    return False

def log_sms_message(recipient, message, status, message_id=None, error=None):
    """Log SMS message for audit trail"""
    try:
        # Create SMS Log document if it exists
        if frappe.db.exists("DocType", "SMS Log"):
            sms_log = frappe.new_doc("SMS Log")
            sms_log.recipient = recipient
            sms_log.message = message
            sms_log.status = status
            sms_log.message_id = message_id
            sms_log.error_message = error
            sms_log.sent_time = now_datetime()
            sms_log.insert()
            return sms_log.name
        else:
            # Log to error log if SMS Log DocType doesn't exist
            log_message = f"SMS to {recipient}: {status} - {message[:50]}..."
            if error:
                log_message += f" - Error: {error}"
            frappe.log_error(log_message, "SMS Activity")
    
    except Exception as e:
        frappe.log_error(f"Failed to log SMS: {str(e)}", "SMS Logging Error")

def send_booking_confirmation_sms(member, booking_data):
    """Send booking confirmation SMS"""
    member_doc = frappe.get_doc("Club Member", member)
    
    message = f"""
    Booking Confirmed!
    Facility: {booking_data.get('facility_name')}
    Date: {booking_data.get('booking_date')}
    Time: {booking_data.get('start_time')}
    Amount: AED {booking_data.get('grand_total')}
    - Social Club
    """
    
    return send_sms(member_doc.mobile_no, message.strip())

def send_event_confirmation_sms(member, event_data):
    """Send event confirmation SMS"""
    member_doc = frappe.get_doc("Club Member", member)
    
    message = f"""
    Event Registration Confirmed!
    Event: {event_data.get('event_name')}
    Date: {event_data.get('event_date')}
    Time: {event_data.get('event_time')}
    Ticket: {event_data.get('ticket_number')}
    - Social Club
    """
    
    return send_sms(member_doc.mobile_no, message.strip())

def send_payment_reminder_sms(member, payment_data):
    """Send payment reminder SMS"""
    member_doc = frappe.get_doc("Club Member", member)
    
    message = f"""
    Payment Reminder!
    Invoice: {payment_data.get('invoice_number')}
    Amount: AED {payment_data.get('amount_due')}
    Due: {payment_data.get('due_date')}
    Please pay to avoid service interruption.
    - Social Club
    """
    
    return send_sms(member_doc.mobile_no, message.strip())

def send_membership_expiry_sms(member, expiry_data):
    """Send membership expiry SMS"""
    member_doc = frappe.get_doc("Club Member", member)
    
    days_until_expiry = expiry_data.get('days_until_expiry')
    urgency = "URGENT: " if days_until_expiry <= 7 else ""
    
    message = f"""
    {urgency}Membership Expiry Reminder!
    Your membership expires in {days_until_expiry} days.
    Renew now to continue enjoying club benefits.
    - Social Club
    """
    
    return send_sms(member_doc.mobile_no, message.strip())

@frappe.whitelist()
def send_custom_sms(recipient, message):
    """Send custom SMS (for admin use)"""
    if not frappe.has_permission("System Manager"):
        return {"success": False, "error": "Permission denied"}
    
    try:
        success = send_sms(recipient, message)
        return {"success": success}
    except Exception as e:
        return {"success": False, "error": str(e)}

def validate_uae_mobile_number(mobile):
    """Validate UAE mobile number format"""
    import re
    
    # UAE mobile formats: +971-5X-XXX-XXXX or 05X-XXX-XXXX
    uae_patterns = [
        r'^\+971-5[0-9]-[0-9]{3}-[0-9]{4}$',
        r'^05[0-9]-[0-9]{3}-[0-9]{4}$',
        r'^\+9715[0-9]{8}$',
        r'^05[0-9]{8}$'
    ]
    
    for pattern in uae_patterns:
        if re.match(pattern, mobile):
            return True
    
    return False

def format_uae_mobile_number(mobile):
    """Format mobile number to standard UAE format"""
    # Remove all non-digit characters
    digits = ''.join(filter(str.isdigit, mobile))
    
    # Add country code if missing
    if len(digits) == 10 and digits.startswith('05'):
        return f"+971{digits[1:]}"
    elif len(digits) == 12 and digits.startswith('971'):
        return f"+{digits}"
    elif len(digits) == 13 and digits.startswith('971'):
        return f"+{digits}"
    else:
        return mobile
