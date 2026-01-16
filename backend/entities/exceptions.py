import logging

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger('entities.exceptions')

class EntityBaseException(Exception):

    """
    Base exception class for entity-related errors.

    Attributes:
        message (str): The error message describing the failure.
        code (str): A specific code for the error type (default: 'entity_error').

    """

    default_message = _("An error occurred in the entities app.")
    default_code = "entity_error"

    def __init__(self, message=None, code=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        super().__init__(self.message)

class EntityValidationError(EntityBaseException, ValidationError):

    """
    Base exception for entity validation errors, extending Django's ValidationError.

    Handles validation failures for entity-related data, supporting single error messages,
    lists of errors, or field-specific error dictionaries. Includes custom error codes and details.

    Attributes:
        message (str or dict or list): The error message(s) describing the validation failure.
        code (str): A specific code for the error type (e.g., 'invalid_name', 'missing_gstin').
        details (dict): Additional context about the error (e.g., invalid fields, values).

    Example:
        # Single error
        raise EntityValidationError("Entity name is required.", code="missing_name")

        # Multiple field errors
        raise EntityValidationError(
            {"name": "Entity name is required", "entity_type": "Invalid entity type"},
            code="invalid_fields",
            details={"fields": ["name", "entity_type"]}
        )

    """

    valid_codes = [
        'entity_error', 'invalid_fields', 'multiple_errors',
        # Entity fields
        'missing_name', 'invalid_name', 'duplicate_name', 'invalid_entity_type',
        'invalid_status', 'invalid_website', 'invalid_registration_number',
        'invalid_entity_size', 'invalid_notes', 'invalid_default_address', 'invalid_user',
        'invalid_industry', 'invalid_parent', 'retrieve_error', 'list_error',
        # Tax compliance
        'missing_gstin', 'missing_pan', 'gstin_state_mismatch',
        # Relationships
        'invalid_address', 'invalid_contact', 'invalid_tax_profile', 'remove_default_address',
        'missing_office_address', 'invalid_entity_mapping',
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
        super().__init__(message, code=code or "entity_validation_error")
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
            return f"Entity validation error: {', '.join(f'{k}: {v}' for k, v in self.message.items())}"
        elif isinstance(self.message, list):
            return f"Entity validation error: {', '.join(str(m) for m in self.message)}"
        return super().__str__()

class InactiveEntityError(EntityValidationError):

    """Raised when an operation is attempted on an inactive entity."""

    default_message = _("Cannot perform operation on an inactive entity.")
    default_code = "inactive_entity"

    def __init__(self, message=None, code=None, details=None):
        super().__init__(message or self.default_message, code or self.default_code, details)

class IndianTaxComplianceError(EntityValidationError):

    """Raised for Indian tax compliance issues (e.g., missing GSTIN/PAN, GSTIN state code mismatch)."""

    default_message = _("Indian tax compliance validation failed.")
    default_code = "indian_tax_compliance"

    def __init__(self, message=None, code=None, details=None):
        super().__init__(message or self.default_message, code or self.default_code, details)

class InvalidEntityMappingError(EntityValidationError):

    """Raised when an invalid entity mapping is provided."""

    default_message = _("Invalid or missing entity mapping.")
    default_code = "invalid_entity_mapping"

    def __init__(self, message=None, code=None, details=None):
        super().__init__(message or self.default_message, code or self.default_code, details)
