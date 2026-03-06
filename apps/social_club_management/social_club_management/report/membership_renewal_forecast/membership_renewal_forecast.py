import frappe
from frappe.utils import add_months, getdate, flt

def execute(filters=None):
    """Generate membership renewal forecast report"""
    
    # Get filter values
    months = filters.get("months", 12) if filters else 12
    
    columns = [
        {
            "fieldname": "month",
            "label": "Month",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "expiring_members",
            "label": "Expiring Members",
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "expected_revenue",
            "label": "Expected Revenue (AED)",
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "renewal_rate",
            "label": "Expected Renewal Rate (%)",
            "fieldtype": "Percent",
            "width": 120
        },
        {
            "fieldname": "projected_revenue",
            "label": "Projected Revenue (AED)",
            "fieldtype": "Currency",
            "width": 150
        }
    ]
    
    data = []
    
    # Get historical renewal rate (default 80% if no data)
    renewal_rate = get_historical_renewal_rate()
    
    # Generate forecast for each month
    for i in range(months):
        forecast_date = add_months(getdate(), i)
        month_start = forecast_date.replace(day=1)
        
        # Get memberships expiring in this month
        expiring_count = frappe.db.count("Club Member", {
            "expiry_date": ["between", [month_start, add_months(month_start, 1)]],
            "membership_status": "Active"
        })
        
        # Calculate expected revenue
        expected_revenue = frappe.db.sql("""
            SELECT SUM(mt.annual_fee) as total
            FROM `tabClub Member` cm
            JOIN `tabMembership Type` mt ON cm.membership_type = mt.name
            WHERE cm.expiry_date BETWEEN %s AND %s
            AND cm.membership_status = 'Active'
        """, (month_start, add_months(month_start, 1)))[0][0] or 0
        
        # Calculate projected revenue based on renewal rate
        projected_revenue = expected_revenue * (renewal_rate / 100)
        
        data.append({
            "month": month_start.strftime("%B %Y"),
            "expiring_members": expiring_count,
            "expected_revenue": flt(expected_revenue),
            "renewal_rate": renewal_rate,
            "projected_revenue": flt(projected_revenue)
        })
    
    return columns, data

def get_historical_renewal_rate():
    """Calculate historical renewal rate"""
    # Get renewals from last 6 months
    six_months_ago = add_months(getdate(), -6)
    
    # Count total expiring members
    total_expiring = frappe.db.count("Club Member", {
        "expiry_date": [">=", six_months_ago],
        "membership_status": "Active"
    })
    
    if total_expiring == 0:
        return 80  # Default renewal rate
    
    # Count renewed members
    renewed_count = frappe.db.sql("""
        SELECT COUNT(DISTINCT cm.name) as count
        FROM `tabClub Member` cm
        JOIN `tabSales Invoice` si ON si.customer = cm.name
        WHERE cm.expiry_date >= %s
        AND si.posting_date >= cm.expiry_date
        AND si.posting_date <= DATE_ADD(cm.expiry_date, INTERVAL 30 DAY)
        AND si.item LIKE '%Membership Renewal%'
        AND si.docstatus = 1
    """, (six_months_ago,))[0][0] or 0
    
    renewal_rate = (renewed_count / total_expiring) * 100
    return round(renewal_rate, 1)

@frappe.whitelist()
def get_renewal_forecast_chart_data(months=12):
    """Get renewal forecast data for charts"""
    columns, data = execute({"months": months})
    
    chart_data = {
        "labels": [row["month"] for row in data],
        "datasets": [
            {
                "name": "Expiring Members",
                "values": [row["expiring_members"] for row in data]
            },
            {
                "name": "Projected Revenue (AED)",
                "values": [row["projected_revenue"] for row in data]
            }
        ]
    }
    
    return chart_data
