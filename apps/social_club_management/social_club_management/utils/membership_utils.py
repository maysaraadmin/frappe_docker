import frappe
from frappe.utils import today, add_days, add_years, getdate, flt
from datetime import datetime, timedelta

def send_membership_expiry_reminders():
    """Send membership expiry reminders to all members"""
    settings = frappe.get_single("Member Portal Settings")
    if not settings or not settings.membership_expiry_reminder:
        return
    
    # Get reminder periods from settings or use defaults
    reminder_days = [30, 15, 7]  # Default reminder days
    
    for days in reminder_days:
        expiry_date = add_days(today(), days)
        
        # Get members expiring on this date
        members = frappe.db.get_all("Club Member",
            filters={
                "expiry_date": expiry_date,
                "membership_status": "Active"
            },
            fields=["name", "full_name", "email", "membership_tier", "expiry_date"]
        )
        
        for member in members:
            # Get renewal fee
            membership_type = frappe.db.get_value("Club Member", member.name, "membership_type")
            renewal_fee = frappe.db.get_value("Membership Type", membership_type, "annual_fee") or 0
            
            expiry_data = {
                "days_until_expiry": days,
                "expiry_date": member.expiry_date,
                "renewal_fee": renewal_fee
            }
            
            settings.send_notification("membership_expiry", member.name, expiry_data)

def generate_renewal_invoices():
    """Generate renewal invoices for expiring memberships"""
    # Get members expiring in next 7 days
    expiry_date = add_days(today(), 7)
    
    members = frappe.db.get_all("Club Member",
        filters={
            "expiry_date": expiry_date,
            "membership_status": "Active"
        },
        fields=["name", "full_name", "membership_type"]
    )
    
    for member in members:
        # Check if renewal invoice already exists
        existing_invoice = frappe.db.exists("Sales Invoice", {
            "customer": member.name,
            "status": ["!=", "Cancelled"],
            "posting_date": [">=", today()]
        })
        
        if existing_invoice:
            continue
        
        # Get membership fee
        membership_type_doc = frappe.get_doc("Membership Type", member.membership_type)
        annual_fee = membership_type_doc.annual_fee
        
        if annual_fee <= 0:
            continue
        
        # Create renewal invoice
        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = member.name
        invoice.due_date = member.expiry_date
        invoice.currency = "AED"
        
        # Add membership renewal item
        item_code = frappe.db.get_single_value("Member Portal Settings", "membership_renewal_item_code")
        if not item_code:
            item_code = "Membership Renewal"
        
        invoice.append("items", {
            "item_code": item_code,
            "item_name": f"Membership Renewal - {membership_type_doc.membership_name}",
            "description": f"Annual membership renewal for {member.full_name}",
            "qty": 1,
            "rate": annual_fee,
            "amount": annual_fee
        })
        
        # Add VAT
        vat_rate = frappe.db.get_single_value("UAE VAT Settings", "vat_rate") or 5
        invoice.append("taxes", {
            "charge_type": "On Net Total",
            "account_head": frappe.db.get_single_value("UAE VAT Settings", "vat_account"),
            "rate": vat_rate
        })
        
        invoice.insert()
        
        # Send notification
        settings = frappe.get_single("Member Portal Settings")
        if settings:
            settings.send_notification("payment_reminder", member.name, {
                "invoice_number": invoice.name,
                "invoice_date": invoice.posting_date,
                "due_date": invoice.due_date,
                "amount_due": invoice.grand_total
            })

def update_membership_status():
    """Update membership status based on expiry dates"""
    # Expire memberships past expiry date
    frappe.db.sql("""
        UPDATE `tabClub Member` 
        SET membership_status = 'Expired' 
        WHERE expiry_date < %s AND membership_status = 'Active'
    """, (today(),))
    
    # Get newly expired members
    expired_members = frappe.db.get_all("Club Member",
        filters={
            "expiry_date": ["<", today()],
            "membership_status": "Expired"
        },
        fields=["name", "full_name", "email"]
    )
    
    # Send notifications for expired memberships
    for member in expired_members:
        frappe.sendmail(
            recipients=[member.email],
            subject="Membership Expired",
            message=f"""
            Dear {member.full_name},
            
            Your membership has expired. Please renew your membership to continue enjoying club facilities.
            
            You can renew online through the member portal or visit the club reception.
            
            Best regards,
            Social Club Management Team
            """
        )

def calculate_membership_statistics():
    """Calculate membership statistics for dashboard"""
    stats = {
        "total_members": 0,
        "active_members": 0,
        "expired_members": 0,
        "suspended_members": 0,
        "pending_members": 0,
        "new_members_this_month": 0,
        "renewals_this_month": 0
    }
    
    # Total members
    stats["total_members"] = frappe.db.count("Club Member")
    
    # Members by status
    for status in ["Active", "Expired", "Suspended", "Pending"]:
        count = frappe.db.count("Club Member", {"membership_status": status})
        stats[f"{status.lower()}_members"] = count
    
    # New members this month
    first_day_of_month = today().replace(day=1)
    stats["new_members_this_month"] = frappe.db.count("Club Member", {
        "creation_date": [">=", first_day_of_month]
    })
    
    # Renewals this month (members who renewed this month)
    stats["renewals_this_month"] = frappe.db.sql("""
        SELECT COUNT(DISTINCT customer) as count
        FROM `tabSales Invoice`
        WHERE posting_date >= %s
        AND item LIKE '%Membership Renewal%'
        AND docstatus = 1
    """, (first_day_of_month,))[0][0]
    
    return stats

def get_membership_renewal_forecast(months=12):
    """Get membership renewal forecast for next N months"""
    forecast = []
    
    for i in range(months):
        forecast_date = add_months(today(), i)
        month_start = forecast_date.replace(day=1)
        
        # Get memberships expiring in this month
        expiring_count = frappe.db.count("Club Member", {
            "expiry_date": ["between", [month_start, add_days(month_start, 30)]],
            "membership_status": "Active"
        })
        
        # Calculate expected revenue
        expected_revenue = frappe.db.sql("""
            SELECT SUM(mt.annual_fee) as total
            FROM `tabClub Member` cm
            JOIN `tabMembership Type` mt ON cm.membership_type = mt.name
            WHERE cm.expiry_date BETWEEN %s AND %s
            AND cm.membership_status = 'Active'
        """, (month_start, add_days(month_start, 30)))[0][0] or 0
        
        forecast.append({
            "month": month_start.strftime("%B %Y"),
            "expiring_members": expiring_count,
            "expected_revenue": flt(expected_revenue)
        })
    
    return forecast

@frappe.whitelist()
def get_member_dashboard_data(member):
    """Get dashboard data for a specific member"""
    member_doc = frappe.get_doc("Club Member", member)
    
    # Get upcoming bookings
    upcoming_bookings = frappe.db.get_all("Facility Booking",
        filters={
            "member": member,
            "booking_date": [">=", today()],
            "status": ["!=", "Cancelled"]
        },
        fields=["facility", "booking_date", "booking_datetime", "end_datetime", "grand_total"],
        order_by="booking_date asc",
        limit=5
    )
    
    # Get upcoming events
    upcoming_events = frappe.db.get_all("Event Registration",
        filters={
            "member": member,
            "status": ["in", ["Registered", "Confirmed"]]
        },
        fields=["event", "registration_date", "total_fee"],
        order_by="registration_date desc",
        limit=5
    )
    
    # Get outstanding invoices
    outstanding_invoices = frappe.db.get_all("Sales Invoice",
        filters={
            "customer": member,
            "status": ["!=", "Paid"],
            "docstatus": 1
        },
        fields=["name", "posting_date", "grand_total", "due_date"],
        order_by="due_date asc"
    )
    
    return {
        "member_info": member_doc.as_dict(),
        "upcoming_bookings": upcoming_bookings,
        "upcoming_events": upcoming_events,
        "outstanding_invoices": outstanding_invoices,
        "account_balance": member_doc.account_balance,
        "credit_limit": member_doc.credit_limit
    }
