from decimal import Decimal

"""Constants for the invoices app."""

# Tax exemption status choices
TAX_EXEMPTION_CHOICES = [
    ('NONE', 'None'),
    ('EXEMPT', 'Tax Exempt'),
    ('ZERO_RATED', 'Zero-Rated'),
]

# GST rate type choices
GST_RATE_TYPE_CHOICES = [
    ('STANDARD', 'Standard'),
    ('EXEMPT', 'Exempt'),
    ('ZERO_RATED', 'Zero-Rated'),
]

# Valid GST rates
VALID_GST_RATES = [
    Decimal('0.00'),
    Decimal('2.50'),
    Decimal('5.00'),
    Decimal('7.50'),
    Decimal('9.00'),
    Decimal('12.00'),
    Decimal('15.00'),
    Decimal('18.00'),
    Decimal('28.00'),
    Decimal('40.00'),
]

# Invoice status codes
INVOICE_STATUS_CODES = {
    'DRAFT': 'Draft',
    'SENT': 'Sent',
    'PAID': 'Paid',
    'PARTIALLY_PAID': 'Partially Paid',
    'CANCELLED': 'Cancelled',
    'OVERDUE': 'Overdue',
}

# Payment status codes
PAYMENT_STATUS_CODES = {
    'PENDING': 'Pending',
    'COMPLETED': 'Completed',
    'FAILED': 'Failed',
    'REFUNDED': 'Refunded',
}

# Billing schedule status codes
BILLING_STATUS_CODES = {
    'ACTIVE': 'Active',
    'PAUSED': 'Paused',
    'COMPLETED': 'Completed',
    'CANCELLED': 'Cancelled',
}

# Payment method codes
PAYMENT_METHOD_CODES = {
    'UPI': 'Unified Payments Interface',
    'CC': 'Credit Card',
    'DC': 'Debit Card',
    'NEFT': 'National Electronic Funds Transfer',
    'RTGS': 'Real Time Gross Settlement',
    'CASH': 'Cash',
    'CHEQUE': 'Cheque',
    'BANK_TRANSFER': 'Bank Transfer',
    'WIRE_TRANSFER': 'Wire Transfer',
    'DIRECT_DEBIT': 'Direct Debit',
    'PAYPAL': 'PayPal',
    'STRIPE': 'Stripe',
    'DIGITAL_WALLET': 'Digital Wallet',
    'ACH': 'Automated Clearing House',
    'SEPA': 'Single Euro Payments Area',
    'MOBILE_PAYMENT': 'Mobile Payment',
    'PREPAID_CARD': 'Prepaid Card',
    'INSTANT_PAYMENT': 'Instant Payment',
    'CRYPTOCURRENCY': 'Cryptocurrency',
}

# HSN/SAC code regex for validation
# HSN_SAC_CODE_REGEX = r'^\d{4,8}$'
HSN_SAC_CODE_REGEX = r'^(HSN|SAC)\s\d{4,8}$'

# Maximum lengths for fields
INVOICE_NUMBER_MAX_LENGTH = 20
PAYMENT_REFERENCE_MAX_LENGTH = 100
DESCRIPTION_MAX_LENGTH = 255
GSTIN_MAX_LENGTH = 15
HSN_SAC_CODE_MAX_LENGTH = 8
PAYMENT_METHOD_CODE_MAX_LENGTH = 20
PAYMENT_METHOD_NAME_MAX_LENGTH = 100

# Billing frequency choices
BILLING_FREQUENCY_CHOICES = [
    ('WEEKLY', 'Weekly'),
    ('MONTHLY', 'Monthly'),
    ('QUARTERLY', 'Quarterly'),
    ('YEARLY', 'Yearly'),
]

# Payment terms choices
PAYMENT_TERMS_CHOICES = [
    ('NET_30', 'Net 30'),
    ('NET_60', 'Net 60'),
    ('NET_90', 'Net 90'),
    ('DUE_ON_RECEIPT', 'Due on Receipt'),
]

# Maximum lengths for fields
INVOICE_NUMBER_MAX_LENGTH = 30
PAYMENT_REFERENCE_MAX_LENGTH = 100
DESCRIPTION_MAX_LENGTH = 255
GSTIN_MAX_LENGTH = 15
HSN_SAC_CODE_MAX_LENGTH = 8
PAYMENT_METHOD_CODE_MAX_LENGTH = 20
PAYMENT_METHOD_NAME_MAX_LENGTH = 100
STATUS_NAME_MAX_LENGTH = 50
STATUS_CODE_MAX_LENGTH = 20
