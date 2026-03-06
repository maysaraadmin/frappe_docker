# Social Club Management System

A comprehensive ERPNext-based management system for UAE social clubs, handling memberships, bookings, events, billing, and compliance.

## Features

### Membership Management
- Member registration with profile management
- Multiple membership tiers (Individual, Family, Corporate, VIP)
- Family account linking
- Automated renewal processing
- Membership status tracking
- Referral program integration

### Facility Booking
- Real-time availability calendar
- Online booking system
- Pricing based on membership tier
- Cancellation policies
- Maintenance scheduling
- Utilization reporting

### Event Management
- Event creation and management
- Online registration system
- Capacity management
- Waitlist functionality
- QR code ticketing
- Attendance tracking

### Financial Management
- UAE VAT compliance (5%)
- VAT 201 return generation
- Automated invoicing
- Payment gateway integration
- Member account charging
- Financial reporting

### Member Portal
- Self-service booking
- Event registration
- Profile management
- Payment history
- Account statements
- Mobile-responsive design

### Compliance
- UAE VAT compliance
- FTA reporting
- Audit trail
- Data retention policies
- Multi-currency support

## Installation

1. Copy the app to your ERPNext apps directory
2. Install the app using bench:
   ```bash
   bench install-app social_club_management
   ```
3. Migrate the database:
   ```bash
   bench migrate
   ```
4. Build assets:
   ```bash
   bench build
   ```

## Configuration

### VAT Settings
1. Go to UAE VAT Settings
2. Configure company TRN
3. Set VAT accounts
4. Configure tax templates

### Member Portal Settings
1. Go to Member Portal Settings
2. Configure portal URL
3. Set up payment gateway
4. Configure SMS gateway
5. Set notification preferences

### Membership Types
1. Create Membership Types
2. Set pricing and privileges
3. Configure renewal rules
4. Set up reminder schedules

## API Endpoints

### Member Portal API
- `member_login` - Member authentication
- `get_member_profile` - Get member details
- `update_member_profile` - Update member information
- `get_member_bookings` - Get facility bookings
- `get_member_events` - Get event registrations
- `get_member_invoices` - Get payment history
- `get_available_facilities` - Get facility availability
- `create_facility_booking` - Create booking
- `get_upcoming_events` - Get upcoming events
- `register_for_event` - Register for event
- `get_member_dashboard` - Get dashboard data

### VAT API
- `get_vat_summary` - Get VAT summary
- `generate_vat_201_return` - Generate VAT return
- `validate_vat_compliance` - Validate compliance
- `export_vat_excel` - Export VAT data

## Reports

### Membership Reports
- Membership Renewal Forecast
- Member Statistics
- Family Account Summary
- Referral Program Report

### Facility Reports
- Facility Utilization Report
- Booking Trends Analysis
- Maintenance Schedule Report
- Peak Hours Analysis

### Financial Reports
- VAT 201 Return
- Revenue by Category
- Payment Gateway Reconciliation
- Member Account Balances

### Event Reports
- Event Attendance Report
- Event Revenue Analysis
- Waitlist Management Report

## Scheduled Tasks

The system includes automated tasks:
- Membership expiry reminders
- Renewal invoice generation
- VAT return generation
- Data backup
- Compliance checks

## Integration

### Payment Gateways
- Telr
- Network International
- Stripe
- PayPal

### SMS Gateways
- Custom SMS API integration
- UAE mobile number validation
- Message templates

### Biometric Systems
- Attendance tracking integration
- Employee time tracking
- Payroll integration

## Security

- Role-based access control
- Session management
- Data encryption
- Audit logging
- GDPR compliance

## Support

For support and documentation:
- Email: maysara.mubarak.mohamed@gmail.com
- Documentation: [Link to documentation]

## License

This app is licensed under GPL-3.0.

## Version History

### v1.0.0
- Initial release
- Core membership management
- Facility booking system
- Event management
- UAE VAT compliance
- Member portal
- Basic reporting
