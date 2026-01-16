import logging

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger('users.exceptions')

class UserBaseException(Exception):

    """Base exception for user-related errors."""

    default_message = _("An error occurred in the users app.")
    default_code = "user_error"

    def __init__(self, message=None, code=None, details=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.details = details or {}
        super().__init__(self.message)

class EmployeeValidationError(UserBaseException, ValidationError):

    """Exception for employee validation errors."""

    valid_codes = [
        'user_error', 'invalid_fields', 'multiple_errors',
        'invalid_employee_code', 'duplicate_employee_code', 'duplicate_email',
        'invalid_hire_date', 'invalid_termination_date', 'invalid_salary',
        'invalid_manager', 'invalid_national_id', 'invalid_phone_number',
        'invalid_department', 'invalid_role', 'invalid_team', 'invalid_employment_status',
        'invalid_employee_type', 'inactive_employee', 'invalid_probation_date',
        'invalid_contract_date', 'invalid_leave_balance', 'invalid_leave_application',
        'invalid_reset_date', 'employee_creation_failed','employee_update_failed',
        'employee_soft_delete_error', 'employee_restore_error'
    ]

    def __init__(self, message, code=None, details=None):
        if code and code not in self.valid_codes:
            logger.error(f"Invalid error code: {code}. Must be one of {self.valid_codes}")
            raise ValueError(f"Invalid error code: {code}")
        super().__init__(message, code or "employee_validation_error", details)

    def to_dict(self):
        """Convert exception to dictionary for API responses."""
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
        if isinstance(self.message, dict):
            return f"Employee validation error: {', '.join(f'{k}: {v}' for k, v in self.message.items())}"
        elif isinstance(self.message, list):
            return f"Employee validation error: {', '.join(str(m) for m in self.message)}"
        return super().__str__()

class MemberValidationError(UserBaseException, ValidationError):

    """Exception for member validation errors."""

    valid_codes = [
        'user_error', 'invalid_fields', 'multiple_errors',
        'invalid_member_code', 'duplicate_member_code', 'duplicate_email',
        'duplicate_sso_id', 'invalid_sso_provider', 'invalid_phone_number',
        'account_deleted', 'invalid_status', 'unverified_member',
        'invalid_permissions', 'invalid_signup_request', 'invalid_password_reset',
        'member_creation_failed','member_update_failed', 'missing_master_data',
        'signup_request_failed', 'member_activation_failed', 'email_error',
        'member_soft_delete_error', 'member_restore_error', 'email_unverified',
    ]

    def __init__(self, message, code=None, details=None):
        if code and code not in self.valid_codes:
            logger.error(f"Invalid error code: {code}. Must be one of {self.valid_codes}")
            raise ValueError(f"Invalid error code: {code}")
        super().__init__(message, code or "member_validation_error", details)

    def to_dict(self):
        """Convert exception to dictionary for API responses."""
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
        if isinstance(self.message, dict):
            return f"Member validation error: {', '.join(f'{k}: {v}' for k, v in self.message.items())}"
        elif isinstance(self.message, list):
            return f"Member validation error: {', '.join(str(m) for m in self.message)}"
        return super().__str__()

class LeaveValidationError(UserBaseException, ValidationError):

    """Exception for leave-related validation errors."""

    valid_codes = [
        'user_error', 'invalid_leave_type', 'invalid_leave_balance',
        'invalid_leave_application', 'insufficient_balance', 'invalid_dates',
        'invalid_hours', 'invalid_approver', 'invalid_reset_date'
    ]

    def __init__(self, message, code=None, details=None):
        if code and code not in self.valid_codes:
            logger.error(f"Invalid error code: {code}. Must be one of {self.valid_codes}")
            raise ValueError(f"Invalid error code: {code}")
        super().__init__(message, code or "leave_validation_error", details)

    def to_dict(self):
        """Convert exception to dictionary for API responses."""
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
        if isinstance(self.message, dict):
            return f"Leave validation error: {', '.join(f'{k}: {v}' for k, v in self.message.items())}"
        elif isinstance(self.message, list):
            return f"Leave validation error: {', '.join(str(m) for m in self.message)}"
        return super().__str__()

class TeamValidationError(UserBaseException, ValidationError):

    """Exception for team validation errors."""

    valid_codes = [
        'user_error', 'invalid_fields', 'multiple_errors',
        'invalid_team_name', 'duplicate_team_name', 'invalid_leader',
        'invalid_department'
    ]

    def __init__(self, message, code=None, details=None):
        if code and code not in self.valid_codes:
            logger.error(f"Invalid error code: {code}. Must be one of {self.valid_codes}")
            raise ValueError(f"Invalid error code: {code}")
        super().__init__(message, code or "team_validation_error", details)

    def to_dict(self):
        """Convert exception to dictionary for API responses."""
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
        if isinstance(self.message, dict):
            return f"Team validation error: {', '.join(f'{k}: {v}' for k, v in self.message.items())}"
        elif isinstance(self.message, list):
            return f"Team validation error: {', '.join(str(m) for m in self.message)}"
        return super().__str__()

class AddressValidationError(UserBaseException, ValidationError):

    """Exception for address validation errors."""

    valid_codes = [
        'user_error', 'invalid_fields', 'multiple_errors',
        'invalid_address', 'invalid_country', 'invalid_postal_code','address_restore_error',
    ]

    def __init__(self, message, code=None, details=None):
        if code and code not in self.valid_codes:
            logger.error(f"Invalid error code: {code}. Must be one of {self.valid_codes}")
            raise ValueError(f"Invalid error code: {code}")
        super().__init__(message, code or "address_validation_error", details)

    def to_dict(self):
        """Convert exception to dictionary for API responses."""
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
        if isinstance(self.message, dict):
            return f"Address validation error: {', '.join(f'{k}: {v}' for k, v in self.message.items())}"
        elif isinstance(self.message, list):
            return f"Address validation error: {', '.join(str(m) for m in self.message)}"
        return super().__str__()


class SupportTicketError(ValidationError):
    def __init__(self, message, code=None, details=None):
        super().__init__(message, code=code)
        self.details = details or {}
