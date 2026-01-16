import logging

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

class FincoreBaseException(Exception):

    """
    Base exception class for fincore-related errors.

    Attributes:
        message (str): The error message describing the failure.
        code (str): A specific code for the error type (default: 'fincore_error').

    """

    default_message = _("An error occurred in the fincore app.")
    default_code = "fincore_error"

    def __init__(self, message=None, code=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        super().__init__(self.message)

class FincoreValidationError(FincoreBaseException, ValidationError):

    """
    Base exception for fincore validation errors, extending Django's ValidationError.

    Handles validation failures for fincore-related data, supporting single error messages,
    lists of errors, or field-specific error dictionaries. Includes custom error codes and details.

    Attributes:
        message (str or dict or list): The error message(s) describing the validation failure.
        code (str): A specific code for the error type (e.g., 'missing_entity', 'invalid_postal_code').
        details (dict): Additional context about the error (e.g., invalid fields, values).

    Example:
        # Single error
        raise FincoreValidationError("Entity is required.", code="missing_entity")

        # Multiple field errors
        raise FincoreValidationError(
            {"street_address": "Street address is required", "city": "City is required"},
            code="invalid_fields",
            details={"fields": ["street_address", "city"]}
        )

    """

    valid_codes = [
        'fincore_error', 'invalid_fields', 'multiple_errors',
        # Address fields
        'missing_entity_mapping', 'missing_city', 'missing_country', 'missing_street_address',
        'invalid_postal_code', 'invalid_subregion', 'invalid_region', 'duplicate_address',
        # Contact fields
        'missing_name', 'missing_contact_info', 'invalid_phone_number', 'invalid_email',
        'duplicate_contact',
        # TaxProfile fields
        'missing_tax_identifier', 'invalid_gstin', 'missing_exemption_reason',
        'invalid_pan', 'duplicate_tax_profile', 'invalid_entity_mapping'
    ]

    def __init__(self, message=None, code=None, details=None):
        """Initialize the exception with a message, optional code, and details."""
        self.details = details or {}
        if code and code not in self.valid_codes:
            logger.error(f"Invalid error code: {code}. Must be one of: {self.valid_codes}")
            raise ValueError(f"Invalid error code: {code}. Must be one of {self.valid_codes}.")
        super().__init__(message, code=code or "fincore_validation_error")
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
            return f"Fincore validation error: {', '.join(f'{k}: {v}' for k, v in self.message.items())}"
        elif isinstance(self.message, list):
            return f"Fincore validation error: {', '.join(str(m) for m in self.message)}"
        return super().__str__()

class InactiveFincoreError(FincoreValidationError):

    """Raised when an operation is attempted on an inactive fincore record."""

    default_message = 'Cannot perform operation on an inactive record.'
    default_code='fincore_error'

    def __init__(self, message=None, code=None, details=None):
        super().__init__(message or self.default_message, code or self.default_code, details)

class AddressValidationError(FincoreValidationError):

    """Raised for address-specific validation issues."""

    default_message = 'Address validation failed.'
    default_code = 'address_validation'

    def __init__(self, message=None, code=None, details=None):
        super().__init__(message or self.default_message, code or self.default_code, details)

class ContactValidationError(FincoreValidationError):

    """Raised for contact-specific validation issues."""

    default_message = 'Contact validation failed.'
    default_code = 'contact_validation'

    def __init__(self, message=None, code=None, details=None):
        super().__init__(message or self.default_message, code or self.default_code, details)

class TaxProfileValidationError(FincoreValidationError):

    """Raised for tax profile-specific validation issues."""

    default_message = 'Tax profile validation failed.'
    default_code = 'tax_profile_validation'

    def __init__(self, message=None, code=None, details=None):
        super().__init__(message or self.default_message, code or self.default_code, details)

class InvalidEntityMappingError(FincoreValidationError):

    """Raised when an invalid entity mapping is provided."""

    default_message = _("Invalid or missing entity mapping.")
    default_code = "invalid_entity_mapping"

    def __init__(self, message=None, code=None, details=None):
        super().__init__(message or self.default_message, code or self.default_code, details)
