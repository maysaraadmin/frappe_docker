# Requirements Document

## Introduction

This document specifies the requirements for a Social Club Management System built on ERPNext for UAE social clubs. The system manages memberships, billing, facility bookings, events, F&B operations, financials, HR/payroll, and provides a member self-service portal. The system ensures compliance with UAE VAT regulations, FTA requirements, UAE Labour Law, and IFRS accounting standards.

## Glossary

- **System**: The Social Club Management System built on ERPNext
- **Member**: An individual registered with the social club
- **Family_Account**: A membership account linking multiple family members
- **Membership_Tier**: A classification level (Individual, Family, Corporate, VIP) with specific privileges
- **Facility**: A bookable resource such as tennis courts, swimming pools, or function halls
- **Booking**: A reservation of a facility for a specific time slot
- **Event**: A club-organized activity with registration and capacity limits
- **Invoice**: A billing document for membership fees, facility bookings, or F&B charges
- **Payment_Gateway**: External service for processing online payments
- **VAT**: Value Added Tax at 5% as per UAE regulations
- **FTA**: Federal Tax Authority of UAE
- **VAT_201_Return**: UAE tax return form for VAT reporting
- **Member_Portal**: Web interface for member self-service
- **POS**: Point of Sale system for F&B transactions
- **WPS_File**: Wage Protection System file for UAE salary transfers
- **EOS**: End of Service benefits as per UAE Labour Law
- **Biometric_System**: External attendance tracking hardware
- **SMS_Gateway**: External service for sending SMS notifications
- **Audit_Trail**: Immutable log of all financial transactions
- **Custom_Report**: User-defined report with configurable parameters
- **Dashboard**: Visual display of key performance metrics
- **Membership_Status**: Current state of membership (Active, Expired, Suspended, Pending)


## Requirements

### Requirement 1: Member Registration

**User Story:** As a club administrator, I want to register new members with complete profile information, so that I can maintain accurate member records.

#### Acceptance Criteria

1. WHEN a new member registration is submitted, THE System SHALL create a Member record with name, contact details, nationality, and emergency contact
2. WHEN a member registration is submitted, THE System SHALL assign a unique member ID
3. WHEN a Family membership type is selected, THE System SHALL create a Family_Account linking all family members
4. THE System SHALL validate that email addresses are unique across all members
5. THE System SHALL validate that mobile numbers follow UAE format (+971-XX-XXX-XXXX)

### Requirement 2: Membership Tier Assignment

**User Story:** As a club administrator, I want to assign membership tiers to members, so that I can control access privileges and pricing.

#### Acceptance Criteria

1. WHEN a Member is created, THE System SHALL assign a Membership_Tier from the available options (Individual, Family, Corporate, VIP)
2. THE System SHALL store the tier-specific privileges and pricing rules with each Membership_Tier
3. WHEN a Membership_Tier is assigned, THE System SHALL apply the corresponding annual fee to the Member
4. THE System SHALL allow modification of Membership_Tier with administrator approval

### Requirement 3: Membership Renewal Processing

**User Story:** As a club administrator, I want to process membership renewals automatically, so that members maintain continuous access to club facilities.

#### Acceptance Criteria

1. WHEN a membership expiry date is 30 days away, THE System SHALL generate a renewal Invoice
2. WHEN a renewal Invoice is paid, THE System SHALL extend the membership expiry date by one year
3. WHEN a membership expires without payment, THE System SHALL update Membership_Status to Expired
4. THE System SHALL send email notifications at 30, 15, and 7 days before expiry

### Requirement 4: Membership Status Tracking

**User Story:** As a club administrator, I want to track membership status in real-time, so that I can enforce access controls.

#### Acceptance Criteria

1. THE System SHALL maintain Membership_Status for each Member (Active, Expired, Suspended, Pending)
2. WHEN a membership payment is received, THE System SHALL update Membership_Status to Active
3. WHEN a membership expires, THE System SHALL update Membership_Status to Expired
4. WHILE Membership_Status is Expired or Suspended, THE System SHALL prevent facility bookings by that Member

### Requirement 5: Recurring Invoice Generation

**User Story:** As a finance manager, I want to generate recurring invoices for membership fees, so that billing is automated and consistent.

#### Acceptance Criteria

1. WHEN a membership anniversary date arrives, THE System SHALL generate an Invoice for the annual membership fee
2. THE System SHALL apply the pricing from the Member's assigned Membership_Tier
3. THE System SHALL calculate VAT at 5% on all invoices
4. THE System SHALL send the Invoice to the Member via email within 24 hours of generation

### Requirement 6: UAE VAT Calculation

**User Story:** As a finance manager, I want VAT calculated correctly on all transactions, so that the club complies with UAE tax regulations.

#### Acceptance Criteria

1. THE System SHALL apply 5% VAT to all taxable transactions
2. THE System SHALL store the VAT amount separately from the base amount in each Invoice
3. THE System SHALL generate VAT-compliant invoices with TRN (Tax Registration Number)
4. THE System SHALL maintain separate accounts for VAT collected and VAT paid

### Requirement 7: Payment Gateway Integration

**User Story:** As a member, I want to pay invoices online, so that I can complete payments conveniently.

#### Acceptance Criteria

1. WHEN a Member selects online payment, THE System SHALL redirect to the Payment_Gateway
2. WHEN the Payment_Gateway confirms payment, THE System SHALL mark the Invoice as paid
3. WHEN the Payment_Gateway reports a failed payment, THE System SHALL update the Invoice status to Failed
4. THE System SHALL store the payment gateway transaction ID with each payment record

### Requirement 8: Facility Booking Calendar

**User Story:** As a member, I want to view facility availability in real-time, so that I can book available time slots.

#### Acceptance Criteria

1. THE System SHALL display a calendar view showing all Facility availability
2. WHEN a Booking is created, THE System SHALL immediately mark that time slot as unavailable
3. THE System SHALL prevent double-booking of the same Facility for overlapping time periods
4. THE System SHALL display Bookings in 30-minute time slot increments

### Requirement 9: Facility Booking Creation

**User Story:** As a member, I want to book facilities online, so that I can reserve resources for my use.

#### Acceptance Criteria

1. WHILE Membership_Status is Active, THE System SHALL allow the Member to create Bookings
2. WHEN a Booking is created, THE System SHALL validate that the requested time slot is available
3. WHEN a Booking is confirmed, THE System SHALL generate an Invoice for the booking fee
4. THE System SHALL apply tier-specific pricing based on the Member's Membership_Tier
5. THE System SHALL send a booking confirmation email within 5 minutes

### Requirement 10: Facility Booking Cancellation

**User Story:** As a member, I want to cancel bookings, so that I can free up slots I no longer need.

#### Acceptance Criteria

1. WHEN a Member cancels a Booking more than 24 hours before the scheduled time, THE System SHALL issue a full refund
2. WHEN a Member cancels a Booking less than 24 hours before the scheduled time, THE System SHALL apply a 50% cancellation fee
3. WHEN a Booking is cancelled, THE System SHALL mark the time slot as available
4. THE System SHALL send a cancellation confirmation email within 5 minutes

### Requirement 11: Event Registration

**User Story:** As a member, I want to register for club events, so that I can participate in activities.

#### Acceptance Criteria

1. WHEN an Event has available capacity, THE System SHALL allow Member registration
2. WHEN Event capacity is reached, THE System SHALL prevent further registrations
3. WHEN a Member registers for an Event, THE System SHALL generate an Invoice for the event fee
4. THE System SHALL send event confirmation with date, time, and location details

### Requirement 12: Event Capacity Management

**User Story:** As an event coordinator, I want to enforce capacity limits, so that events are not overbooked.

#### Acceptance Criteria

1. THE System SHALL store a maximum capacity value for each Event
2. THE System SHALL track the current registration count for each Event
3. WHEN registration count equals maximum capacity, THE System SHALL mark the Event as full
4. WHILE an Event is marked as full, THE System SHALL prevent new registrations

### Requirement 13: Event Ticketing

**User Story:** As a member, I want to receive event tickets, so that I have proof of registration.

#### Acceptance Criteria

1. WHEN an Event registration is paid, THE System SHALL generate a ticket with unique QR code
2. THE System SHALL send the ticket to the Member via email as a PDF attachment
3. THE System SHALL store the QR code for validation at event check-in
4. WHEN a QR code is scanned, THE System SHALL validate the ticket and mark it as used

### Requirement 14: POS Transaction Processing

**User Story:** As an F&B staff member, I want to process sales transactions, so that I can charge members for food and beverages.

#### Acceptance Criteria

1. WHEN an F&B transaction is initiated, THE System SHALL display available menu items with prices
2. WHEN items are selected, THE System SHALL calculate the total including 5% VAT
3. WHERE the customer is a Member, THE System SHALL allow charging to the member account
4. WHEN a transaction is completed, THE System SHALL generate an Invoice linked to the Member

### Requirement 15: F&B Inventory Management

**User Story:** As an F&B manager, I want to track inventory levels, so that I can prevent stockouts.

#### Acceptance Criteria

1. WHEN an F&B item is sold, THE System SHALL decrement the inventory quantity
2. WHEN inventory quantity falls below the reorder level, THE System SHALL generate a purchase requisition
3. THE System SHALL track inventory movements with date, quantity, and user information
4. THE System SHALL calculate inventory valuation using weighted average cost method

### Requirement 16: Member Account Charging

**User Story:** As a member, I want to charge F&B purchases to my account, so that I can pay later in a consolidated invoice.

#### Acceptance Criteria

1. WHILE Membership_Status is Active, THE System SHALL allow charging to member account
2. WHEN a charge is posted, THE System SHALL create an Invoice line item linked to the Member
3. THE System SHALL enforce a credit limit based on Membership_Tier
4. WHEN account balance exceeds credit limit, THE System SHALL require immediate payment

### Requirement 17: Financial Reporting for IFRS

**User Story:** As a finance manager, I want financial reports compliant with IFRS, so that the club meets accounting standards.

#### Acceptance Criteria

1. THE System SHALL generate Balance Sheet, Income Statement, and Cash Flow Statement
2. THE System SHALL classify accounts according to IFRS chart of accounts structure
3. THE System SHALL support accrual-based accounting with automatic journal entries
4. THE System SHALL generate comparative reports for current and prior periods

### Requirement 18: UAE VAT 201 Return Generation

**User Story:** As a finance manager, I want to generate VAT 201 returns, so that I can file with FTA.

#### Acceptance Criteria

1. THE System SHALL calculate total VAT collected for the reporting period
2. THE System SHALL calculate total VAT paid on purchases for the reporting period
3. THE System SHALL generate a VAT_201_Return with all required fields per FTA specifications
4. THE System SHALL export the VAT_201_Return in Excel format compatible with FTA portal

### Requirement 19: Financial Audit Trail

**User Story:** As an auditor, I want an immutable audit trail of all financial transactions, so that I can verify accounting accuracy.

#### Acceptance Criteria

1. WHEN a financial transaction is created, THE System SHALL record it in the Audit_Trail with timestamp and user
2. THE System SHALL prevent deletion or modification of posted financial transactions
3. THE System SHALL log all attempts to modify financial records with user and timestamp
4. THE System SHALL allow filtering Audit_Trail by date range, user, and transaction type

### Requirement 20: Employee Attendance Tracking

**User Story:** As an HR manager, I want to track employee attendance, so that I can calculate payroll accurately.

#### Acceptance Criteria

1. WHEN the Biometric_System records a clock-in, THE System SHALL create an attendance record
2. WHEN the Biometric_System records a clock-out, THE System SHALL update the attendance record with exit time
3. THE System SHALL calculate total working hours from clock-in and clock-out times
4. THE System SHALL flag attendance records with missing clock-out as incomplete

### Requirement 21: UAE Labour Law EOS Calculation

**User Story:** As an HR manager, I want to calculate end of service benefits, so that I comply with UAE Labour Law.

#### Acceptance Criteria

1. WHEN an employee is terminated, THE System SHALL calculate EOS based on years of service
2. THE System SHALL apply 21 days of basic salary per year for the first 5 years of service
3. THE System SHALL apply 30 days of basic salary per year for service beyond 5 years
4. THE System SHALL generate an EOS statement with calculation breakdown

### Requirement 22: WPS File Generation

**User Story:** As an HR manager, I want to generate WPS files, so that I can process salary payments through UAE banks.

#### Acceptance Criteria

1. WHEN payroll is processed, THE System SHALL generate a WPS_File in SIF format
2. THE System SHALL include employee ID, salary amount, and bank details in the WPS_File
3. THE System SHALL validate that all required fields are present before generating the file
4. THE System SHALL export the WPS_File compatible with UAE bank portals

### Requirement 23: Member Portal Authentication

**User Story:** As a member, I want to log into the member portal securely, so that I can access my account.

#### Acceptance Criteria

1. WHEN a Member enters valid credentials, THE System SHALL authenticate and grant access to Member_Portal
2. WHEN a Member enters invalid credentials three times, THE System SHALL lock the account for 15 minutes
3. THE System SHALL require password complexity of minimum 8 characters with letters and numbers
4. THE System SHALL send a password reset link via email when requested

### Requirement 24: Member Portal Self-Service Booking

**User Story:** As a member, I want to book facilities through the portal, so that I can reserve resources without calling the club.

#### Acceptance Criteria

1. WHEN a Member logs into Member_Portal, THE System SHALL display available facilities
2. THE System SHALL allow the Member to select date, time, and Facility for booking
3. WHEN a Booking is submitted, THE System SHALL validate availability and create the Booking
4. THE System SHALL display booking confirmation with details and payment link

### Requirement 25: Member Portal Payment History

**User Story:** As a member, I want to view my payment history, so that I can track my spending.

#### Acceptance Criteria

1. WHEN a Member accesses payment history in Member_Portal, THE System SHALL display all Invoices
2. THE System SHALL show Invoice date, description, amount, VAT, and payment status
3. THE System SHALL allow filtering by date range and payment status
4. THE System SHALL allow downloading Invoices as PDF files

### Requirement 26: Member Portal Profile Management

**User Story:** As a member, I want to update my profile information, so that my contact details are current.

#### Acceptance Criteria

1. THE System SHALL allow Members to update email, mobile number, and address through Member_Portal
2. WHEN email is changed, THE System SHALL send a verification link to the new email
3. WHEN mobile number is changed, THE System SHALL send a verification code via SMS_Gateway
4. THE System SHALL prevent changes to member ID and membership tier without administrator approval

### Requirement 27: Management Dashboard

**User Story:** As a club manager, I want to view key metrics on a dashboard, so that I can monitor club performance.

#### Acceptance Criteria

1. THE System SHALL display a Dashboard with active membership count, revenue, and facility utilization
2. THE System SHALL update Dashboard metrics in real-time as transactions occur
3. THE System SHALL display trend charts for membership growth and revenue over the past 12 months
4. THE System SHALL allow filtering Dashboard data by date range and membership tier

### Requirement 28: Custom Report Builder

**User Story:** As a club manager, I want to create custom reports, so that I can analyze specific business questions.

#### Acceptance Criteria

1. THE System SHALL provide a report builder interface for creating Custom_Reports
2. THE System SHALL allow selection of data fields from Member, Invoice, Booking, and Event entities
3. THE System SHALL allow filtering by date range, membership tier, and status
4. THE System SHALL export Custom_Reports in Excel and PDF formats

### Requirement 29: SMS Notification Integration

**User Story:** As a club administrator, I want to send SMS notifications to members, so that I can communicate important updates.

#### Acceptance Criteria

1. WHEN a membership is about to expire, THE System SHALL send an SMS reminder via SMS_Gateway
2. WHEN a Booking is confirmed, THE System SHALL send an SMS confirmation via SMS_Gateway
3. WHEN an Event registration is confirmed, THE System SHALL send an SMS confirmation via SMS_Gateway
4. THE System SHALL log all SMS messages with timestamp, recipient, and delivery status

### Requirement 30: Payment Gateway Transaction Reconciliation

**User Story:** As a finance manager, I want to reconcile payment gateway transactions, so that I can ensure all payments are accounted for.

#### Acceptance Criteria

1. THE System SHALL import transaction reports from Payment_Gateway daily
2. THE System SHALL match Payment_Gateway transactions to Invoices by transaction ID
3. WHEN a transaction cannot be matched, THE System SHALL flag it for manual review
4. THE System SHALL generate a reconciliation report showing matched and unmatched transactions

### Requirement 31: Multi-Currency Support

**User Story:** As a finance manager, I want to handle transactions in multiple currencies, so that I can accommodate international members.

#### Acceptance Criteria

1. THE System SHALL store a base currency of AED (UAE Dirham)
2. WHERE a transaction is in a foreign currency, THE System SHALL convert to AED using the exchange rate on transaction date
3. THE System SHALL store both the original currency amount and the AED equivalent
4. THE System SHALL display amounts in the Member's preferred currency in Member_Portal

### Requirement 32: Data Backup and Recovery

**User Story:** As a system administrator, I want automated backups, so that I can recover data in case of failure.

#### Acceptance Criteria

1. THE System SHALL create a full database backup daily at 2:00 AM
2. THE System SHALL retain daily backups for 30 days
3. THE System SHALL create incremental backups every 6 hours
4. THE System SHALL verify backup integrity after each backup operation

### Requirement 33: Role-Based Access Control

**User Story:** As a system administrator, I want to control user permissions, so that staff only access functions relevant to their role.

#### Acceptance Criteria

1. THE System SHALL define roles for Administrator, Finance Manager, HR Manager, F&B Staff, and Member
2. THE System SHALL assign permissions to each role for create, read, update, and delete operations
3. WHEN a user attempts an unauthorized action, THE System SHALL deny access and log the attempt
4. THE System SHALL allow Administrators to create custom roles with specific permissions

### Requirement 34: Email Notification Configuration

**User Story:** As a club administrator, I want to configure email templates, so that I can customize member communications.

#### Acceptance Criteria

1. THE System SHALL provide default email templates for membership renewal, booking confirmation, and event registration
2. THE System SHALL allow customization of email subject, body, and footer
3. THE System SHALL support template variables for member name, invoice amount, and booking details
4. THE System SHALL preview emails before sending

### Requirement 35: Facility Maintenance Scheduling

**User Story:** As a facilities manager, I want to schedule maintenance periods, so that facilities are unavailable during maintenance.

#### Acceptance Criteria

1. WHEN a maintenance period is scheduled for a Facility, THE System SHALL block that time slot from booking
2. THE System SHALL display maintenance periods on the booking calendar with a distinct indicator
3. WHEN a maintenance period overlaps with existing Bookings, THE System SHALL notify affected Members
4. THE System SHALL allow cancellation of maintenance periods to reopen availability

### Requirement 36: Member Referral Tracking

**User Story:** As a marketing manager, I want to track member referrals, so that I can reward members who bring new members.

#### Acceptance Criteria

1. WHEN a new Member is registered, THE System SHALL allow entry of a referring Member ID
2. WHEN a referred Member completes payment, THE System SHALL credit the referring Member with a referral bonus
3. THE System SHALL generate a referral report showing total referrals per Member
4. THE System SHALL apply referral bonuses as account credits usable for future invoices

### Requirement 37: Event Waitlist Management

**User Story:** As an event coordinator, I want to manage waitlists for full events, so that I can fill cancellations automatically.

#### Acceptance Criteria

1. WHEN an Event is at full capacity, THE System SHALL allow Members to join a waitlist
2. WHEN a registered Member cancels, THE System SHALL automatically offer the spot to the first Member on the waitlist
3. THE System SHALL send a notification to the waitlisted Member with 24 hours to confirm
4. WHEN the waitlisted Member does not confirm within 24 hours, THE System SHALL offer the spot to the next Member

### Requirement 38: Membership Suspension

**User Story:** As a club administrator, I want to suspend memberships, so that I can enforce club policies.

#### Acceptance Criteria

1. WHEN a Member violates club policies, THE System SHALL allow an Administrator to update Membership_Status to Suspended
2. WHILE Membership_Status is Suspended, THE System SHALL prevent the Member from creating Bookings or Event registrations
3. WHILE Membership_Status is Suspended, THE System SHALL prevent Member_Portal login
4. THE System SHALL record the suspension reason and date in the Member record

### Requirement 39: Financial Year-End Closing

**User Story:** As a finance manager, I want to close the financial year, so that I can start a new accounting period.

#### Acceptance Criteria

1. WHEN year-end closing is initiated, THE System SHALL calculate profit or loss for the year
2. THE System SHALL transfer profit or loss to retained earnings
3. THE System SHALL prevent modifications to transactions in closed periods
4. THE System SHALL generate year-end financial statements for the closed period

### Requirement 40: Compliance Reporting

**User Story:** As a compliance officer, I want to generate regulatory reports, so that I can meet UAE regulatory requirements.

#### Acceptance Criteria

1. THE System SHALL generate monthly revenue reports by category
2. THE System SHALL generate quarterly VAT summary reports
3. THE System SHALL generate annual membership statistics reports
4. THE System SHALL export all compliance reports in Excel and PDF formats with digital signatures
