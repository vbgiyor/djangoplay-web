import logging

from django.core.exceptions import ValidationError

logger = logging.getLogger('industries.exceptions')


class InvalidIndustryData(ValidationError):

    """
    Raised when industry data (e.g., code, description, level, sector, parent) fails validation.

    This exception extends Django's ValidationError to provide structured handling
    for validation failures across Industry model operations. It supports single error messages,
    lists of errors, or field-specific error dictionaries, and includes custom error codes
    for programmatic handling.

    Example:
        # Single field error
        raise InvalidIndustryData("Industry code is invalid.", code="invalid_code")

        # Multiple field errors
        raise InvalidIndustryData(
            {"code": "Invalid format", "parent": "Invalid parent relationship"},
            code="invalid_fields",
            details={"model": "Industry"}
        )

        # Multiple list errors
        raise InvalidIndustryData(
            ["Invalid hierarchy", "Parent level mismatch"],
            code="multiple_errors"
        )

    """

    def __init__(self, message, code=None, details=None):
        """
        Initialize the exception with a message, optional code, and details.

        Args:
            message (str or dict or list): Validation error message(s)
            code (str, optional): Specific error code for industry validations.
            details (dict, optional): Additional context such as model, field, value.

        """
        self.details = details or {}

        valid_codes = [
            'invalid_industry_data', 'invalid_fields', 'multiple_errors', 'retrieve_error',
            # Industry
            'missing_description', 'invalid_description', 'duplicate_code',
            'missing_code', 'invalid_code_format', 'invalid_level',
            'invalid_sector', 'invalid_parent', 'invalid_hierarchy',
        ]

        if code and code not in valid_codes:
            logger.error(f"Invalid error code for industry: {code}. Must be one of {valid_codes}")
            raise ValueError(f"Invalid error code: {code}. Must be one of {valid_codes}.")

        super().__init__(message, code=code or "invalid_industry_data")

    def to_dict(self):
        """
        Convert the exception to a structured dictionary for API responses.

        Returns:
            dict: Contains error message(s), error code, and details context.

        """
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
        """Readable error format."""
        if isinstance(self.message, dict):
            return f"Invalid industry data: {', '.join(f'{k}: {v}' for k, v in self.message.items())}"
        elif isinstance(self.message, list):
            return f"Invalid industry data: {', '.join(str(m) for m in self.message)}"
        return super().__str__()
