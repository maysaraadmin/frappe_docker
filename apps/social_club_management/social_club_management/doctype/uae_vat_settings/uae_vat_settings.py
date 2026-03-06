import frappe
from frappe.model.document import Document
from frappe.utils import today, add_days, add_months, getdate, flt
from datetime import datetime, timedelta
import json

class UAESettings(Document):
    def validate(self):
        self.validate_trn_format()
        self.validate_accounts()
        self.calculate_next_filing_date()
        
    def validate_trn_format(self):
        """Validate UAE TRN format"""
        if self.company_trn:
            # UAE TRN should be 15 digits starting with specific prefixes
            trn = self.company_trn.replace("-", "").replace(" ", "")
            if len(trn) != 15 or not trn.isdigit():
                frappe.throw("Company TRN must be 15 digits")
            
            # Valid TRN prefixes for UAE
            valid_prefixes = ['100', '101', '102', '103', '104', '105', '106', '107']
            prefix = trn[:3]
            if prefix not in valid_prefixes:
                frappe.throw("Invalid TRN format for UAE")
    
    def validate_accounts(self):
        """Ensure all required VAT accounts are set"""
        required_accounts = ['vat_account', 'vat_payable_account', 'vat_receivable_account']
        for account in required_accounts:
            if not self.get(account):
                frappe.throw(f"{account.replace('_', ' ').title()} is required")
    
    def calculate_next_filing_date(self):
        """Calculate next VAT filing date"""
        if not self.last_filing_date:
            return
        
        if self.filing_frequency == "Quarterly":
            # Next filing is 3 months after last filing
            next_date = add_months(getdate(self.last_filing_date), 3)
        else:
            # Monthly filing
            next_date = add_months(getdate(self.last_filing_date), 1)
        
        self.next_filing_date = next_date
    
    def before_save(self):
        self.set_system_fields()
    
    def set_system_fields(self):
        self.created_by = frappe.session.user
        self.modified_by = frappe.session.user
    
    def get_vat_return_data(self, start_date, end_date):
        """Generate VAT return data for the specified period"""
        # Get all sales invoices for the period
        sales_invoices = frappe.db.get_all("Sales Invoice",
            filters={
                "posting_date": ["between", [start_date, end_date]],
                "docstatus": 1
            },
            fields=["name", "grand_total", "base_total_taxes_and_charges", "customer"]
        )
        
        # Get all purchase invoices for the period
        purchase_invoices = frappe.db.get_all("Purchase Invoice",
            filters={
                "posting_date": ["between", [start_date, end_date]],
                "docstatus": 1
            },
            fields=["name", "grand_total", "base_total_taxes_and_charges", "supplier"]
            )
        
        # Calculate totals
        total_sales = sum([inv.grand_total for inv in sales_invoices])
        total_vat_collected = sum([inv.base_total_taxes_and_charges for inv in sales_invoices])
        total_purchases = sum([inv.grand_total for inv in purchase_invoices])
        total_vat_paid = sum([inv.base_total_taxes_and_charges for inv in purchase_invoices])
        
        # Calculate net VAT payable/receivable
        net_vat = total_vat_collected - total_vat_paid
        
        return {
            "period_start": start_date,
            "period_end": end_date,
            "total_sales": total_sales,
            "total_vat_collected": total_vat_collected,
            "total_purchases": total_purchases,
            "total_vat_paid": total_vat_paid,
            "net_vat_payable": net_vat if net_vat > 0 else 0,
            "net_vat_receivable": abs(net_vat) if net_vat < 0 else 0,
            "sales_invoices": sales_invoices,
            "purchase_invoices": purchase_invoices
        }
    
    def generate_vat_201_return(self, period_start=None, period_end=None):
        """Generate VAT 201 return in FTA format"""
        if not period_start or not period_end:
            # Default to last quarter/month
            if self.filing_frequency == "Quarterly":
                period_end = add_months(today(), -1)
                period_start = add_months(period_end, -3)
            else:
                period_end = add_months(today(), -1)
                period_start = add_months(period_end, -1)
        
        vat_data = self.get_vat_return_data(period_start, period_end)
        
        # Create VAT 201 return structure
        vat_return = {
            "trn": self.company_trn,
            "tax_period": {
                "start_date": period_start,
                "end_date": period_end
            },
            "taxable_supplies": {
                "standard_rated": vat_data["total_sales"],
                "zero_rated": 0,  # Would need to calculate from zero-rated items
                "exempt": 0,  # Would need to calculate from exempt items
                "designated_zone": 0  # Would need to calculate from designated zone supplies
            },
            "vat_collected": {
                "standard_rate": vat_data["total_vat_collected"],
                "zero_rate": 0,
                "exempt": 0,
                "designated_zone": 0
            },
            "vat_recoverable": {
                "imports": vat_data["total_vat_paid"],
                "local_purchases": 0,  # Would need to calculate from local purchases
                "reverse_charge": 0  # Would need to calculate from reverse charge
            },
            "vat_payable": {
                "net_vat": vat_data["net_vat_payable"]
            }
        }
        
        return vat_return
    
    def export_vat_201_excel(self, vat_return_data):
        """Export VAT 201 return data in Excel format"""
        # This would generate Excel file in FTA format
        # For now, return CSV-like structure
        headers = [
            "TRN", "Tax Period Start", "Tax Period End",
            "Standard Rated Supplies", "VAT on Standard Rated",
            "Zero Rated Supplies", "VAT on Zero Rated",
            "Exempt Supplies", "VAT on Exempt",
            "VAT Recoverable", "Net VAT Payable"
        ]
        
        data = [
            vat_return_data["trn"],
            vat_return_data["tax_period"]["start_date"],
            vat_return_data["tax_period"]["end_date"],
            vat_return_data["taxable_supplies"]["standard_rated"],
            vat_return_data["vat_collected"]["standard_rate"],
            vat_return_data["taxable_supplies"]["zero_rated"],
            vat_return_data["vat_collected"]["zero_rate"],
            vat_return_data["taxable_supplies"]["exempt"],
            vat_return_data["vat_collected"]["exempt"],
            vat_return_data["vat_recoverable"]["imports"],
            vat_return_data["vat_payable"]["net_vat"]
        ]
        
        return {"headers": headers, "data": data}
    
    def validate_vat_compliance(self):
        """Validate VAT compliance for transactions"""
        compliance_issues = []
        
        # Check if all sales invoices have proper VAT
        sales_invoices = frappe.db.get_all("Sales Invoice",
            filters={"docstatus": 1},
            fields=["name", "grand_total", "base_total_taxes_and_charges"]
        )
        
        for invoice in sales_invoices:
            if invoice.grand_total > 0 and invoice.base_total_taxes_and_charges == 0:
                compliance_issues.append(f"Sales Invoice {invoice.name} has no VAT")
        
        # Check TRN on customers
        customers_without_trn = frappe.db.get_all("Customer",
            filters={"tax_id": ["is", "not set"]},
            fields=["name", "customer_name"]
        )
        
        for customer in customers_without_trn:
            compliance_issues.append(f"Customer {customer.name} - {customer.customer_name} has no TRN")
        
        return compliance_issues
    
    def send_vat_reminder(self):
        """Send VAT filing reminder"""
        if not self.next_filing_date or not self.send_vat_reminders:
            return
        
        days_until_filing = (getdate(self.next_filing_date) - today()).days
        
        if days_until_filing == self.reminder_days_before_filing:
            # Send reminder email
            finance_managers = frappe.db.get_all("Has Role",
                filters={"role": "Finance Manager"},
                fields=["parent"]
            )
            
            recipient_emails = [user.parent for user in finance_managers]
            
            subject = f"VAT Filing Reminder - Due on {self.next_filing_date}"
            message = f"""
            Dear Finance Manager,
            
            This is a reminder that your VAT return for the period ending {self.next_filing_date} is due for filing.
            
            Please ensure all transactions are properly recorded and VAT calculations are accurate before filing.
            
            Next Filing Date: {self.next_filing_date}
            Days Until Filing: {days_until_filing}
            
            Best regards,
            Social Club Management System
            """
            
            frappe.sendmail(
                recipients=recipient_emails,
                subject=subject,
                message=message
            )
    
    def create_vat_journal_entry(self, vat_amount, date, account_type="payable"):
        """Create journal entry for VAT adjustment"""
        if vat_amount <= 0:
            return
        
        journal_entry = frappe.new_doc("Journal Entry")
        journal_entry.posting_date = date
        journal_entry.company = frappe.defaults.get_defaults().get("company")
        
        # Determine accounts based on type
        if account_type == "payable":
            debit_account = self.vat_payable_account
            credit_account = self.vat_account
        else:
            debit_account = self.vat_receivable_account
            credit_account = self.vat_account
        
        # Add debit entry
        journal_entry.append("accounts", {
            "account": debit_account,
            "debit_in_account_currency": vat_amount,
            "credit_in_account_currency": 0
        })
        
        # Add credit entry
        journal_entry.append("accounts", {
            "account": credit_account,
            "debit_in_account_currency": 0,
            "credit_in_account_currency": vat_amount
        })
        
        journal_entry.insert()
        journal_entry.submit()
        
        return journal_entry.name

@frappe.whitelist()
def get_vat_summary(period_start, period_end):
    """Get VAT summary for dashboard"""
    settings = frappe.get_single("UAE VAT Settings")
    if not settings:
        return {"error": "VAT Settings not configured"}
    
    vat_data = settings.get_vat_return_data(period_start, period_end)
    return vat_data

@frappe.whitelist()
def generate_vat_201_return(period_start=None, period_end=None):
    """Generate VAT 201 return"""
    settings = frappe.get_single("UAE VAT Settings")
    if not settings:
        return {"error": "VAT Settings not configured"}
    
    try:
        vat_return = settings.generate_vat_201_return(period_start, period_end)
        return {"success": True, "data": vat_return}
    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def validate_vat_compliance():
    """Validate VAT compliance"""
    settings = frappe.get_single("UAE VAT Settings")
    if not settings:
        return {"error": "VAT Settings not configured"}
    
    issues = settings.validate_vat_compliance()
    return {"compliance_issues": issues}

@frappe.whitelist()
def export_vat_excel(period_start, period_end):
    """Export VAT data in Excel format"""
    settings = frappe.get_single("UAE VAT Settings")
    if not settings:
        return {"error": "VAT Settings not configured"}
    
    vat_return = settings.generate_vat_201_return(period_start, period_end)
    excel_data = settings.export_vat_201_excel(vat_return)
    
    return excel_data
