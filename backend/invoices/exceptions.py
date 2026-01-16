import logging

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger('invoices.exceptions')

class InvoiceBaseException(Exception):

    """
    Base exception class for invoice-related errors.

    Attributes:
        message (str): The error message describing the failure.
        code (str): A specific code for the error type (default: 'invoice_error').

    """

    default_message = _("An error occurred in the invoices app.")
    default_code = "invoice_error"

    def __init__(self, message=None, code=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        super().__init__(self.message)

class InvoiceValidationError(InvoiceBaseException, ValidationError):

    """
    Base exception for invoice validation errors, extending Django's ValidationError.

    Handles validation failures for invoice-related data, supporting single error messages,
    lists of errors, or field-specific error dictionaries. Includes custom error codes and details.

    Attributes:
        message (str or dict or list): The error message(s) describing the validation failure.
        code (str): A specific code for the error type (e.g., 'invalid_invoice_number', 'inactive_invoice').
        details (dict): Additional context about the error (e.g., invalid fields, values).

    Example:
        # Single error
        raise InvoiceValidationError("Invoice number is required.", code="missing_invoice_number")

        # Multiple field errors
        raise InvoiceValidationError(
            {"invoice_number": "Required", "status": "Invalid status"},
            code="invalid_fields",
            details={"fields": ["invoice_number", "status"]}
        )

    """

    valid_codes = [
        'invoice_error', 'invalid_fields', 'multiple_errors',
        # Invoice fields
        'missing_invoice_number', 'invalid_invoice_number', 'duplicate_invoice_number',
        'invalid_issuer', 'invalid_recipient', 'invalid_billing_address',
        'invalid_billing_country', 'invalid_billing_region',
        'invalid_issue_date', 'invalid_due_date', 'invalid_status',
        'invalid_payment_terms', 'invalid_currency', 'invalid_base_amount',
        'invalid_total_amount', 'invalid_payment_method', 'invalid_payment_reference',
        'invalid_description', 'inactive_invoice', 'inactive_issuer', 'inactive_recipient',
        'total_calculation_failed', 'save_error', 'invoice_soft_delete_error', 'invoice_restore_error',
        'invalid_invoice_object', 'invalid_invoice', 'missing_draft_status',
        # Line items
        'invalid_hsn_sac_code', 'invalid_quantity', 'invalid_unit_price',
        'invalid_discount', 'line_item_total_calculation_failed','inactive_line_item',
        'line_item_soft_delete_error','line_item_restore_error', 'missing_line_items',
        'duplicate_line_item_description', 'no_line_items',
        # Payments
        'invalid_payment_amount', 'invalid_payment_date', 'invalid_payment_status',
        'inactive_payment', 'cancelled_invoice', 'excessive_payment', 'invalid_upi_reference',
        'issuer_gstin_state_mismatch',
        # Billing schedule
        'inactive_entity', 'invalid_end_date', 'invalid_next_billing_date',
        'invalid_billing_amount', 'invalid_billing_status', 'inactive_billing_schedule',
        'billing_schedule_validation_error',
        # Payment method
        'invalid_payment_method_code', 'inactive_payment_method', 'duplicate_payment_reference',
        'payment_status_validation_failed', 'payment_amount_validation_failed', 'payment_reference_validation_failed',
        # Status
        'empty_name', 'empty_code', 'multiple_defaults', 'invalid_locked_status', 'duplicate_status_name', 'duplicate_code',
        'status_validation_failed', 'duplicate_status_code',
        # Additional codes from forms.py
        'missing_customer', 'inactive_customer', 'invalid_billing_schedule',
        'missing_billing_info', 'invalid_billing_location', 'mismatched_region_country',
         'mismatched_cgst_rate', 'mismatched_sgst_rate','mismatched_igst_rate', 'invalid_location_hierarchy',
        # Generic
        'invalid_date', 'invalid_amount', 'invalid_tax_rate', 'invalid_status_code',
        'redis_connection_error', 'invalid_entity_mapping', 'duplicate_billing_schedule', 'invalid_frequency',
        'accessible_entities_failed','line_item_validation_error'
    ]

    def __init__(self, message, code=None, details=None):
        """
        Initialize the exception with a message, optional code, and details.

        Args:
            message (str or dict or list): Error message(s) or error dictionary/list.
            code (str, optional): Specific error code for programmatic handling.
            details (dict, optional): Additional context for the error.

        """
        self.details = details or {}
        if code and code not in self.valid_codes:
            logger.error(f"Invalid error code: {code}. Must be one of {self.valid_codes}")
            raise ValueError(f"Invalid error code: {code}. Must be one of {self.valid_codes}.")
        super().__init__(message, code=code or "invoice_validation_error")
        self.details = details or {}

    def to_dict(self):
        """Convert the exception to a dictionary for API responses."""
        if isinstance(self.message, dict):
            error_message = "Multiple field errors"
            details = {"errors": self.message, **self.details}
        elif isinstance(self.message, list):
            error_message = "Multiple validation errors"
            details = {"errors": self.message, **self.details}
        else:
            error_message = str(self.message)
            details = self.details
        return {
            "error": error_message,
            "code": self.code,
            "details": details,
        }

    def __str__(self):
        """Return a string representation of the error."""
        if isinstance(self.message, dict):
            return f"Invoice validation error: {', '.join(f'{k}: {v}' for k, v in self.message.items())}"
        elif isinstance(self.message, list):
            return f"Invoice validation error: {', '.join(str(m) for m in self.message)}"
        return super().__str__()

class GSTValidationError(InvoiceValidationError):

    """
    Raised for GST-related validation issues.

    Inherits from InvoiceValidationError to reuse its functionality while providing
    GST-specific error codes.

    Example:
        raise GSTValidationError("Invalid GSTIN format.", code="invalid_issuer_gstin")

    """

    default_message = _("GST validation failed.")
    default_code = "gst_validation_error"

    valid_codes = [
        'gst_validation_error', 'invalid_issuer_gstin', 'invalid_recipient_gstin',
        'issuer_gstin_state_mismatch', 'missing_billing_country', 'recipient_gstin_state_mismatch',
        'invalid_cgst_rate', 'invalid_sgst_rate', 'invalid_igst_rate', 'invalid_country',
        'missing_igst_rate', 'invalid_gst_for_inter_state', 'invalid_gst_for_intra_state',
        'inconsistent_gst_rates', 'invalid_hsn_sac_code', 'invalid_effective_dates',
        'invalid_rates_for_exempt', 'inactive_gst_config', 'missing_gstin',
        'mismatched_gstin', 'invalid_gstin', 'unsupported_gst_rate',
        'invalid_reverse_charge', 'gst_config_validation_error',
        'gst_sof_delete_error', 'gst_restore_error', 'mismatched_cgst_rate',
        'mismatched_sgst_rate', 'mismatched_igst_rate','invalid_gst_fields',
        'invalid_igst_amount','invalid_cgst_amount','invalid_sgst_amount',
        'missing_hsn_sac_code','inactive_region','invalid_gst_amounts',
        'already_active_gst_configuration', 'invalid_gstin_format', 'invalid_pan_format',
        'gst_rates_validation_error', 'gst_config_fetch_error','invalid_description',
        'missing_gst_config', 'duplicate_gst_config',
        'interstate_check_error','missing_billing_region','invalid_gst_rate','invalid_gst_config',
        'invalid_gst_rates_interstate', 'gstin_fetch_error','invalid_billing_country',
        'invalid_exemption_rates','invalid_gst_rate_combination',
        'buyer_gstin_address_mismatch', 'seller_gstin_address_mismatch','missing_data','inactive_issuer',
        'inactive_recipient', 'inactive_entity', 'invalid_entity_type', 'invalid_gstin',
        'issuer_gstin_address_mismatch', 'recipient_gstin_address_mismatch','hsn_sac_code_too_long',
        'invalid_gst_rates', 'invalid_issue_date', 'invoice_soft_delete_error',
    ]

    def __init__(self, message=None, code=None, details=None):
        super().__init__(message or self.default_message, code or self.default_code, details)

class InvalidInvoiceStatusError(InvoiceBaseException):

    """
    Raised for invalid invoice status operations.

    Used for errors related to invoice status transitions or operations, not validation of data.

    Example:
        raise InvalidInvoiceStatusError("Cannot change status to PAID.", code="invalid_status_transition")

    """

    default_message = _("Invalid invoice status operation.")
    default_code = "invalid_invoice_status"

    def __init__(self, message=None, code=None, details=None):
        self.details = details or {}
        super().__init__(message or self.default_message, code or self.default_code)
