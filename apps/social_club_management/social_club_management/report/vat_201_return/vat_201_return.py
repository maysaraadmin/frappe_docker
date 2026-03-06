import frappe
from frappe.utils import add_months, getdate, flt

def execute(filters=None):
    """Generate VAT 201 return report"""
    
    # Get filter values
    period_start = filters.get("period_start") if filters else add_months(getdate(), -3)
    period_end = filters.get("period_end") if filters else getdate()
    
    columns = [
        {
            "fieldname": "transaction_type",
            "label": "Transaction Type",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "transaction_count",
            "label": "Count",
            "fieldtype": "Int",
            "width": 80
        },
        {
            "fieldname": "total_amount",
            "label": "Total Amount (AED)",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "vat_amount",
            "label": "VAT Amount (AED)",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "net_amount",
            "label": "Net Amount (AED)",
            "fieldtype": "Currency",
            "width": 120
        }
    ]
    
    data = []
    
    # Get VAT settings
    vat_settings = frappe.get_single("UAE VAT Settings")
    if not vat_settings:
        frappe.throw("UAE VAT Settings not configured")
    
    # Get sales transactions
    sales_data = get_sales_vat_data(period_start, period_end)
    
    # Get purchase transactions
    purchase_data = get_purchase_vat_data(period_start, period_end)
    
    # Add sales data
    for category, items in sales_data.items():
        total_amount = sum([item["amount"] for item in items])
        vat_amount = sum([item["vat"] for item in items])
        net_amount = total_amount - vat_amount
        
        data.append({
            "transaction_type": f"Sales - {category}",
            "transaction_count": len(items),
            "total_amount": flt(total_amount),
            "vat_amount": flt(vat_amount),
            "net_amount": flt(net_amount)
        })
    
    # Add purchase data
    for category, items in purchase_data.items():
        total_amount = sum([item["amount"] for item in items])
        vat_amount = sum([item["vat"] for item in items])
        net_amount = total_amount - vat_amount
        
        data.append({
            "transaction_type": f"Purchase - {category}",
            "transaction_count": len(items),
            "total_amount": flt(total_amount),
            "vat_amount": flt(vat_amount),
            "net_amount": flt(net_amount)
        })
    
    # Add summary rows
    total_sales_vat = sum([row["vat_amount"] for row in data if "Sales" in row["transaction_type"]])
    total_purchase_vat = sum([row["vat_amount"] for row in data if "Purchase" in row["transaction_type"]])
    net_vat_payable = total_sales_vat - total_purchase_vat
    
    data.append({
        "transaction_type": "Total VAT Collected",
        "transaction_count": "",
        "total_amount": "",
        "vat_amount": flt(total_sales_vat),
        "net_amount": ""
    })
    
    data.append({
        "transaction_type": "Total VAT Paid",
        "transaction_count": "",
        "total_amount": "",
        "vat_amount": flt(total_purchase_vat),
        "net_amount": ""
    })
    
    data.append({
        "transaction_type": "Net VAT Payable",
        "transaction_count": "",
        "total_amount": "",
        "vat_amount": flt(net_vat_payable),
        "net_amount": ""
    })
    
    return columns, data

def get_sales_vat_data(period_start, period_end):
    """Get sales VAT data categorized by tax rate"""
    sales_invoices = frappe.db.get_all("Sales Invoice",
        filters={
            "posting_date": ["between", [period_start, period_end]],
            "docstatus": 1
        },
        fields=["name", "grand_total", "base_total_taxes_and_charges", "customer_name"]
    )
    
    # Categorize by VAT rate
    categorized_data = {
        "Standard Rated (5%)": [],
        "Zero Rated (0%)": [],
        "Exempt": []
    }
    
    for invoice in sales_invoices:
        if invoice.base_total_taxes_and_charges > 0:
            # Assume standard rate (5%)
            categorized_data["Standard Rated (5%)"].append({
                "invoice": invoice.name,
                "amount": invoice.grand_total,
                "vat": invoice.base_total_taxes_and_charges
            })
        else:
            # Could be zero rated or exempt - need to check tax template
            tax_template = frappe.db.get_value("Sales Invoice", invoice.name, "taxes_and_charges")
            if tax_template and "zero" in tax_template.lower():
                categorized_data["Zero Rated (0%)"].append({
                    "invoice": invoice.name,
                    "amount": invoice.grand_total,
                    "vat": 0
                })
            else:
                categorized_data["Exempt"].append({
                    "invoice": invoice.name,
                    "amount": invoice.grand_total,
                    "vat": 0
                })
    
    return categorized_data

def get_purchase_vat_data(period_start, period_end):
    """Get purchase VAT data categorized by tax rate"""
    purchase_invoices = frappe.db.get_all("Purchase Invoice",
        filters={
            "posting_date": ["between", [period_start, period_end]],
            "docstatus": 1
        },
        fields=["name", "grand_total", "base_total_taxes_and_charges", "supplier_name"]
    )
    
    # Categorize by VAT rate
    categorized_data = {
        "Standard Rated (5%)": [],
        "Zero Rated (0%)": [],
        "Exempt": [],
        "Reverse Charge": []
    }
    
    for invoice in purchase_invoices:
        if invoice.base_total_taxes_and_charges > 0:
            # Check if reverse charge
            tax_template = frappe.db.get_value("Purchase Invoice", invoice.name, "taxes_and_charges")
            if tax_template and "reverse" in tax_template.lower():
                categorized_data["Reverse Charge"].append({
                    "invoice": invoice.name,
                    "amount": invoice.grand_total,
                    "vat": invoice.base_total_taxes_and_charges
                })
            else:
                categorized_data["Standard Rated (5%)"].append({
                    "invoice": invoice.name,
                    "amount": invoice.grand_total,
                    "vat": invoice.base_total_taxes_and_charges
                })
        else:
            # Could be zero rated or exempt
            tax_template = frappe.db.get_value("Purchase Invoice", invoice.name, "taxes_and_charges")
            if tax_template and "zero" in tax_template.lower():
                categorized_data["Zero Rated (0%)"].append({
                    "invoice": invoice.name,
                    "amount": invoice.grand_total,
                    "vat": 0
                })
            else:
                categorized_data["Exempt"].append({
                    "invoice": invoice.name,
                    "amount": invoice.grand_total,
                    "vat": 0
                })
    
    return categorized_data

@frappe.whitelist()
def export_vat_201_excel(period_start, period_end):
    """Export VAT 201 return in Excel format"""
    columns, data = execute({
        "period_start": period_start,
        "period_end": period_end
    })
    
    # Format for Excel export
    excel_data = []
    excel_data.append([col["label"] for col in columns])
    
    for row in data:
        excel_data.append([
            row["transaction_type"],
            row["transaction_count"],
            row["total_amount"],
            row["vat_amount"],
            row["net_amount"]
        ])
    
    return excel_data

@frappe.whitelist()
def get_vat_summary_chart_data(period_start=None, period_end=None):
    """Get VAT summary data for charts"""
    if not period_start:
        period_start = add_months(getdate(), -3)
    if not period_end:
        period_end = getdate()
    
    columns, data = execute({
        "period_start": period_start,
        "period_end": period_end
    })
    
    # Extract summary data
    total_vat_collected = 0
    total_vat_paid = 0
    
    for row in data:
        if "Sales" in row["transaction_type"] and "Total" not in row["transaction_type"]:
            total_vat_collected += row["vat_amount"]
        elif "Purchase" in row["transaction_type"] and "Total" not in row["transaction_type"]:
            total_vat_paid += row["vat_amount"]
    
    net_vat = total_vat_collected - total_vat_paid
    
    chart_data = {
        "labels": ["VAT Collected", "VAT Paid", "Net VAT Payable"],
        "datasets": [{
            "name": "VAT Amount (AED)",
            "values": [flt(total_vat_collected), flt(total_vat_paid), flt(net_vat)]
        }]
    }
    
    return chart_data
