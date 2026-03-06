import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, add_days, add_hours, get_datetime
from datetime import datetime, timedelta

class Facility(Document):
    def validate(self):
        self.validate_unique_codes()
        self.validate_pricing()
        self.set_default_operating_hours()
        
    def validate_unique_codes(self):
        if self.facility_code:
            existing = frappe.db.exists("Facility", {
                "facility_code": self.facility_code, 
                "name": ["!=", self.name]
            })
            if existing:
                frappe.throw("Facility Code already exists")
    
    def validate_pricing(self):
        if self.member_rate < 0 or self.non_member_rate < 0 or self.vip_rate < 0:
            frappe.throw("Rates cannot be negative")
    
    def set_default_operating_hours(self):
        if not self.operating_hours and self.get("__islocal"):
            # Set default operating hours (7 AM to 11 PM)
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            for day in days:
                self.append("operating_hours", {
                    "day": day,
                    "opening_time": "07:00:00",
                    "closing_time": "23:00:00",
                    "is_closed": 0
                })
    
    def before_save(self):
        self.set_system_fields()
    
    def set_system_fields(self):
        self.created_by = frappe.session.user
        self.modified_by = frappe.session.user
    
    def is_available_at_time(self, booking_datetime, duration_hours):
        """Check if facility is available at given time"""
        if not self.is_available:
            return False, "Facility is not available"
        
        # Check operating hours
        day_name = booking_datetime.strftime("%A")
        operating_hours = self.get_operating_hours_for_day(day_name)
        if not operating_hours or operating_hours.get("is_closed"):
            return False, f"Facility is closed on {day_name}"
        
        # Check if booking time is within operating hours
        booking_end = booking_datetime + timedelta(hours=duration_hours)
        opening_time = datetime.strptime(operating_hours["opening_time"], "%H:%M:%S").time()
        closing_time = datetime.strptime(operating_hours["closing_time"], "%H:%M:%S").time()
        
        if (booking_datetime.time() < opening_time or 
            booking_end.time() > closing_time):
            return False, "Booking time is outside operating hours"
        
        # Check for maintenance
        if self.is_maintenance_scheduled(booking_datetime, booking_end):
            return False, "Facility is under maintenance during this time"
        
        # Check for existing bookings
        if self.has_conflicting_booking(booking_datetime, booking_end):
            return False, "Time slot is already booked"
        
        return True, "Available"
    
    def get_operating_hours_for_day(self, day_name):
        """Get operating hours for specific day"""
        for row in self.operating_hours:
            if row.day == day_name:
                return row.as_dict()
        return None
    
    def is_maintenance_scheduled(self, start_time, end_time):
        """Check if maintenance is scheduled during the booking period"""
        for maintenance in self.maintenance_schedule:
            maintenance_start = get_datetime(maintenance.start_datetime)
            maintenance_end = get_datetime(maintenance.end_datetime)
            
            if (start_time < maintenance_end and end_time > maintenance_start):
                return True
        return False
    
    def has_conflicting_booking(self, start_time, end_time, exclude_booking=None):
        """Check if there are conflicting bookings"""
        filters = {
            "facility": self.name,
            "status": ["!=", "Cancelled"],
            "booking_datetime": ["<", end_time],
            "end_datetime": [">", start_time]
        }
        
        if exclude_booking:
            filters["name"] = ["!=", exclude_booking]
        
        existing_bookings = frappe.db.get_all("Facility Booking", 
            filters=filters,
            limit=1
        )
        
        return len(existing_bookings) > 0
    
    def get_rate_for_member(self, member_tier):
        """Get rate based on member tier"""
        if member_tier == "VIP":
            return self.vip_rate or self.member_rate
        return self.member_rate
    
    def get_available_time_slots(self, date, duration_hours=1):
        """Get available time slots for a given date"""
        available_slots = []
        date_obj = get_datetime(date)
        day_name = date_obj.strftime("%A")
        
        operating_hours = self.get_operating_hours_for_day(day_name)
        if not operating_hours or operating_hours.get("is_closed"):
            return available_slots
        
        opening_time = datetime.strptime(
            f"{date} {operating_hours['opening_time']}", "%Y-%m-%d %H:%M:%S"
        )
        closing_time = datetime.strptime(
            f"{date} {operating_hours['closing_time']}", "%Y-%m-%d %H:%M:%S"
        )
        
        # Generate 30-minute slots
        current_time = opening_time
        slot_duration = timedelta(minutes=30)
        
        while current_time + timedelta(hours=duration_hours) <= closing_time:
            end_time = current_time + timedelta(hours=duration_hours)
            
            is_available, message = self.is_available_at_time(current_time, duration_hours)
            if is_available:
                available_slots.append({
                    "start_time": current_time.strftime("%H:%M"),
                    "end_time": end_time.strftime("%H:%M"),
                    "available": True
                })
            
            current_time += slot_duration
        
        return available_slots

@frappe.whitelist()
def get_facility_list():
    return frappe.db.get_all("Facility",
        filters={"is_available": 1},
        fields=["name", "facility_name", "facility_type", "location", "capacity", "member_rate"]
    )

@frappe.whitelist()
def check_facility_availability(facility, date, time, duration_hours):
    facility_doc = frappe.get_doc("Facility", facility)
    booking_datetime = get_datetime(f"{date} {time}")
    
    is_available, message = facility_doc.is_available_at_time(
        booking_datetime, float(duration_hours)
    )
    
    return {"available": is_available, "message": message}

@frappe.whitelist()
def get_facility_time_slots(facility, date, duration_hours=1):
    facility_doc = frappe.get_doc("Facility", facility)
    return facility_doc.get_available_time_slots(date, float(duration_hours))
