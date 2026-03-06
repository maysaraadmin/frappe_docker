import frappe
from frappe.utils import getdate, add_days, flt

def execute(filters=None):
    """Generate facility utilization report"""
    
    # Get filter values
    from_date = filters.get("from_date") if filters else getdate()
    to_date = filters.get("to_date") if filters else add_days(getdate(), 30)
    facility = filters.get("facility") if filters else None
    
    columns = [
        {
            "fieldname": "facility_name",
            "label": "Facility Name",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "facility_type",
            "label": "Facility Type",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "total_bookings",
            "label": "Total Bookings",
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "total_hours",
            "label": "Total Hours Booked",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "fieldname": "revenue",
            "label": "Revenue (AED)",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "utilization_rate",
            "label": "Utilization Rate (%)",
            "fieldtype": "Percent",
            "width": 120
        },
        {
            "fieldname": "peak_hours",
            "label": "Peak Hours",
            "fieldtype": "Data",
            "width": 120
        }
    ]
    
    data = []
    
    # Build filters
    booking_filters = {
        "booking_date": ["between", [from_date, to_date]],
        "status": ["!=", "Cancelled"]
    }
    
    if facility:
        booking_filters["facility"] = facility
    
    # Get all facilities
    facility_filters = {"is_available": 1}
    if facility:
        facility_filters["name"] = facility
    
    facilities = frappe.db.get_all("Facility",
        filters=facility_filters,
        fields=["name", "facility_name", "facility_type", "member_rate"]
    )
    
    for fac in facilities:
        # Get bookings for this facility
        booking_filters["facility"] = fac.name
        
        bookings = frappe.db.get_all("Facility Booking",
            filters=booking_filters,
            fields=["duration_hours", "grand_total", "booking_datetime"]
        )
        
        if not bookings:
            continue
        
        # Calculate metrics
        total_bookings = len(bookings)
        total_hours = sum([b.duration_hours for b in bookings])
        total_revenue = sum([b.grand_total for b in bookings])
        
        # Calculate utilization rate
        operating_hours_per_day = 16  # Assuming 7 AM to 11 PM
        days_in_period = (getdate(to_date) - getdate(from_date)).days + 1
        total_possible_hours = days_in_period * operating_hours_per_day
        
        utilization_rate = (total_hours / total_possible_hours) * 100 if total_possible_hours > 0 else 0
        
        # Find peak hours
        peak_hours = get_peak_hours(bookings)
        
        data.append({
            "facility_name": fac.facility_name,
            "facility_type": fac.facility_type,
            "total_bookings": total_bookings,
            "total_hours": flt(total_hours, 2),
            "revenue": flt(total_revenue),
            "utilization_rate": flt(utilization_rate, 1),
            "peak_hours": peak_hours
        })
    
    return columns, data

def get_peak_hours(bookings):
    """Find peak booking hours"""
    if not bookings:
        return "N/A"
    
    # Group bookings by hour
    hourly_counts = {}
    for booking in bookings:
        if booking.booking_datetime:
            hour = booking.booking_datetime.hour
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
    
    if not hourly_counts:
        return "N/A"
    
    # Find peak hour
    peak_hour = max(hourly_counts, key=hourly_counts.get)
    
    # Format time range
    peak_start = f"{peak_hour:02d}:00"
    peak_end = f"{(peak_hour + 1) % 24:02d}:00"
    
    return f"{peak_start} - {peak_end}"

@frappe.whitelist()
def get_facility_utilization_chart_data(from_date=None, to_date=None, facility=None):
    """Get facility utilization data for charts"""
    columns, data = execute({
        "from_date": from_date,
        "to_date": to_date,
        "facility": facility
    })
    
    chart_data = {
        "labels": [row["facility_name"] for row in data],
        "datasets": [
            {
                "name": "Utilization Rate (%)",
                "values": [row["utilization_rate"] for row in data]
            },
            {
                "name": "Revenue (AED)",
                "values": [row["revenue"] for row in data]
            }
        ]
    }
    
    return chart_data

@frappe.whitelist()
def get_facility_booking_trends(from_date=None, to_date=None, facility=None):
    """Get booking trends over time"""
    if not from_date:
        from_date = getdate()
    if not to_date:
        to_date = add_days(getdate(), 30)
    
    # Get daily booking counts
    daily_bookings = frappe.db.sql("""
        SELECT 
            DATE(booking_date) as date,
            COUNT(*) as bookings,
            SUM(duration_hours) as total_hours,
            SUM(grand_total) as revenue
        FROM `tabFacility Booking`
        WHERE booking_date BETWEEN %s AND %s
        AND status != 'Cancelled'
        {facility_condition}
        GROUP BY DATE(booking_date)
        ORDER BY date
    """.format(
        facility_condition="AND facility = %s" if facility else ""
    ), (from_date, to_date, facility) if facility else (from_date, to_date))
    
    return {
        "labels": [str(row[0]) for row in daily_bookings],
        "datasets": [
            {
                "name": "Daily Bookings",
                "values": [row[1] for row in daily_bookings]
            },
            {
                "name": "Daily Revenue (AED)",
                "values": [flt(row[3]) for row in daily_bookings]
            }
        ]
    }
