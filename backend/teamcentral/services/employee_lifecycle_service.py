import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from users.exceptions import EmployeeValidationError
from utilities.utils.general.normalize_text import normalize_text
from utilities.utils.locations.phone_number_validations import validate_phone_number

User = get_user_model()

logger = logging.getLogger(__name__)


class EmployeeLifecycleService:

    """
    Employee identity + HR lifecycle (not auth).
    """

    @staticmethod
    def validate_employee_payload(data):
        errors = {}

        if not data.get("email"):
            errors["email"] = "Email is required."

        if data.get("phone_number") and not validate_phone_number(
            data["phone_number"]
        ):
            errors["phone_number"] = "Invalid phone number."

        if errors:
            raise EmployeeValidationError(errors, code="invalid_employee")

        return (
            normalize_text(data.get("first_name", "")),
            normalize_text(data.get("last_name", "")),
            data.get("email").lower().strip(),
        )

    @staticmethod
    @transaction.atomic
    def create_employee(*, data: dict, created_by):
        first, last, email = EmployeeLifecycleService.validate_employee_payload(data)

        employee = User.objects.create_user(
            username=data["username"],
            email=email,
            first_name=first,
            last_name=last,
            department=data["department"],
            role=data["role"],
            employment_status=data["employment_status"],
            employee_type=data["employee_type"],
            is_active=data.get("is_active", True),
            is_verified=data.get("is_verified", False),
            created_by=created_by,
            updated_by=created_by,
        )

        logger.info("Employee created code=%s", employee.employee_code)
        return employee
