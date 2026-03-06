import frappe
from frappe.utils import today, add_days, getdate, flt
from frappe.auth import login, check_password

@frappe.whitelist(allow_guest=True)
def member_login(email, password):
    """Member login for portal access"""
    try:
        # Validate input
        if not email or not password:
            return {"success": False, "error": "Email and password are required"}
        
        # Find user by email
        user = frappe.db.exists("User", {"email": email})
        if not user:
            return {"success": False, "error": "Invalid email or password"}
        
        # Check if user is a member
        member = frappe.db.exists("Club Member", {"email": email})
        if not member:
            return {"success": False, "error": "Not a registered member"}
        
        # Check member status
        member_status = frappe.db.get_value("Club Member", member, "membership_status")
        if member_status in ["Expired", "Suspended"]:
            return {"success": False, "error": f"Membership is {member_status}"}
        
        # Authenticate user
        try:
            login_manager = frappe.auth.LoginManager()
            login_manager.authenticate(user, password)
            login_manager.post_login()
            
            # Generate session token
            session_token = frappe.generate_hash(length=32)
            
            # Store session token
            frappe.cache().set_value(f"member_session_{session_token}", user, expires_in_sec=3600)
            
            return {
                "success": True,
                "session_token": session_token,
                "member": member,
                "user": user
            }
            
        except frappe.AuthenticationError:
            return {"success": False, "error": "Invalid email or password"}
    
    except Exception as e:
        frappe.log_error(f"Member login error: {str(e)}", "Member API")
        return {"success": False, "error": "Login failed. Please try again."}

@frappe.whitelist()
def get_member_profile(member_id):
    """Get member profile information"""
    try:
        # Validate session
        if not validate_member_session(frappe.request.headers.get("Authorization")):
            return {"success": False, "error": "Invalid session"}
        
        member = frappe.get_doc("Club Member", member_id)
        
        # Return member data (excluding sensitive fields)
        member_data = member.as_dict()
        
        # Remove sensitive fields
        sensitive_fields = ["created_by", "modified_by", "creation_date", "modified_date"]
        for field in sensitive_fields:
            member_data.pop(field, None)
        
        return {"success": True, "member": member_data}
    
    except frappe.DoesNotExistError:
        return {"success": False, "error": "Member not found"}
    except Exception as e:
        frappe.log_error(f"Get member profile error: {str(e)}", "Member API")
        return {"success": False, "error": "Failed to get member profile"}

@frappe.whitelist()
def update_member_profile(member_id, updates):
    """Update member profile"""
    try:
        # Validate session
        if not validate_member_session(frappe.request.headers.get("Authorization")):
            return {"success": False, "error": "Invalid session"}
        
        member = frappe.get_doc("Club Member", member_id)
        
        # Allowed fields for member to update
        allowed_fields = ["phone", "mobile_no", "emergency_contact_name", "emergency_contact_phone"]
        
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(member, field, value)
        
        member.save()
        
        return {"success": True, "message": "Profile updated successfully"}
    
    except frappe.DoesNotExistError:
        return {"success": False, "error": "Member not found"}
    except Exception as e:
        frappe.log_error(f"Update member profile error: {str(e)}", "Member API")
        return {"success": False, "error": "Failed to update profile"}

@frappe.whitelist()
def get_member_bookings(member_id, status=None, limit=20):
    """Get member's facility bookings"""
    try:
        # Validate session
        if not validate_member_session(frappe.request.headers.get("Authorization")):
            return {"success": False, "error": "Invalid session"}
        
        filters = {"member": member_id}
        if status:
            filters["status"] = status
        
        bookings = frappe.db.get_all("Facility Booking",
            filters=filters,
            fields=[
                "name", "facility", "booking_date", "booking_datetime", 
                "end_datetime", "duration_hours", "status", "grand_total"
            ],
            order_by="booking_date desc",
            limit=int(limit)
        )
        
        return {"success": True, "bookings": bookings}
    
    except Exception as e:
        frappe.log_error(f"Get member bookings error: {str(e)}", "Member API")
        return {"success": False, "error": "Failed to get bookings"}

@frappe.whitelist()
def get_member_events(member_id, status=None, limit=20):
    """Get member's event registrations"""
    try:
        # Validate session
        if not validate_member_session(frappe.request.headers.get("Authorization")):
            return {"success": False, "error": "Invalid session"}
        
        filters = {"member": member_id}
        if status:
            filters["status"] = status
        
        registrations = frappe.db.get_all("Event Registration",
            filters=filters,
            fields=[
                "name", "event", "registration_date", "status", 
                "total_fee", "ticket_number", "number_of_guests"
            ],
            order_by="registration_date desc",
            limit=int(limit)
        )
        
        # Get event details for each registration
        for reg in registrations:
            event_details = frappe.db.get_value("Club Event", reg.event, 
                ["event_name", "start_date", "start_time", "venue"], as_dict=True)
            reg["event_details"] = event_details
        
        return {"success": True, "events": registrations}
    
    except Exception as e:
        frappe.log_error(f"Get member events error: {str(e)}", "Member API")
        return {"success": False, "error": "Failed to get events"}

@frappe.whitelist()
def get_member_invoices(member_id, status=None, limit=20):
    """Get member's invoices"""
    try:
        # Validate session
        if not validate_member_session(frappe.request.headers.get("Authorization")):
            return {"success": False, "error": "Invalid session"}
        
        filters = {"customer": member_id, "docstatus": 1}
        if status:
            filters["status"] = status
        
        invoices = frappe.db.get_all("Sales Invoice",
            filters=filters,
            fields=[
                "name", "posting_date", "due_date", "grand_total", 
                "outstanding_amount", "status"
            ],
            order_by="posting_date desc",
            limit=int(limit)
        )
        
        return {"success": True, "invoices": invoices}
    
    except Exception as e:
        frappe.log_error(f"Get member invoices error: {str(e)}", "Member API")
        return {"success": False, "error": "Failed to get invoices"}

@frappe.whitelist()
def get_available_facilities(date):
    """Get available facilities for booking"""
    try:
        # Validate session
        if not validate_member_session(frappe.request.headers.get("Authorization")):
            return {"success": False, "error": "Invalid session"}
        
        facilities = frappe.db.get_all("Facility",
            filters={"is_available": 1},
            fields=[
                "name", "facility_name", "facility_type", "location", 
                "capacity", "member_rate", "description"
            ]
        )
        
        # Get availability for each facility
        for facility in facilities:
            facility_doc = frappe.get_doc("Facility", facility.name)
            time_slots = facility_doc.get_available_time_slots(date, 1)
            facility["available_slots"] = time_slots
        
        return {"success": True, "facilities": facilities}
    
    except Exception as e:
        frappe.log_error(f"Get available facilities error: {str(e)}", "Member API")
        return {"success": False, "error": "Failed to get facilities"}

@frappe.whitelist()
def create_facility_booking(member_id, facility, date, time, duration_hours, purpose=""):
    """Create facility booking"""
    try:
        # Validate session
        if not validate_member_session(frappe.request.headers.get("Authorization")):
            return {"success": False, "error": "Invalid session"}
        
        # Import booking function
        from social_club_management.doctype.facility_booking.facility_booking import create_facility_booking
        
        result = create_facility_booking(member_id, facility, date, time, duration_hours, purpose)
        return result
    
    except Exception as e:
        frappe.log_error(f"Create facility booking error: {str(e)}", "Member API")
        return {"success": False, "error": "Failed to create booking"}

@frappe.whitelist()
def get_upcoming_events():
    """Get upcoming events"""
    try:
        # Validate session
        if not validate_member_session(frappe.request.headers.get("Authorization")):
            return {"success": False, "error": "Invalid session"}
        
        events = frappe.db.get_all("Club Event",
            filters={
                "event_status": ["in", ["Published", "Full"]],
                "start_date": [">=", today()]
            },
            fields=[
                "name", "event_name", "event_type", "start_date", 
                "start_time", "venue", "member_fee", "available_spots"
            ],
            order_by="start_date asc",
            limit=50
        )
        
        return {"success": True, "events": events}
    
    except Exception as e:
        frappe.log_error(f"Get upcoming events error: {str(e)}", "Member API")
        return {"success": False, "error": "Failed to get events"}

@frappe.whitelist()
def register_for_event(member_id, event, number_of_guests=0):
    """Register for an event"""
    try:
        # Validate session
        if not validate_member_session(frappe.request.headers.get("Authorization")):
            return {"success": False, "error": "Invalid session"}
        
        # Import registration function
        from social_club_management.doctype.club_event.club_event import register_for_event
        
        result = register_for_event(event, member_id, number_of_guests)
        return result
    
    except Exception as e:
        frappe.log_error(f"Register for event error: {str(e)}", "Member API")
        return {"success": False, "error": "Failed to register for event"}

@frappe.whitelist()
def get_member_dashboard(member_id):
    """Get member dashboard data"""
    try:
        # Validate session
        if not validate_member_session(frappe.request.headers.get("Authorization")):
            return {"success": False, "error": "Invalid session"}
        
        # Import dashboard function
        from social_club_management.utils.membership_utils import get_member_dashboard_data
        
        dashboard_data = get_member_dashboard_data(member_id)
        return {"success": True, "dashboard": dashboard_data}
    
    except Exception as e:
        frappe.log_error(f"Get member dashboard error: {str(e)}", "Member API")
        return {"success": False, "error": "Failed to get dashboard data"}

def validate_member_session(authorization_header):
    """Validate member session token"""
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return False
    
    token = authorization_header.split(" ")[1]
    user_id = frappe.cache().get_value(f"member_session_{token}")
    
    if not user_id:
        return False
    
    # Check if user is still active
    if not frappe.db.exists("User", user_id):
        return False
    
    return True

@frappe.whitelist()
def logout_member(session_token):
    """Logout member session"""
    try:
        frappe.cache().delete_value(f"member_session_{session_token}")
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        return {"success": False, "error": "Failed to logout"}
