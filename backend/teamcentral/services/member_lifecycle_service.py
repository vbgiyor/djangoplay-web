import logging
from typing import TYPE_CHECKING, Optional

from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.db import transaction
from users.exceptions import MemberValidationError
from utilities.utils.general.normalize_text import normalize_text
from utilities.utils.locations.phone_number_validations import validate_phone_number

from teamcentral.models import (
    EmploymentStatus,
    MemberProfile,
    MemberStatus,
)

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

User = get_user_model()

logger = logging.getLogger(__name__)


class MemberLifecycleService:

    """
    Owns MemberProfile lifecycle:
    - create
    - update
    - activate from signup
    """

    @staticmethod
    def validate_member_payload(data, *, instance: MemberProfile | None = None):
        errors = {}

        email = data.get("email")
        if not email:
            errors["email"] = "Email is required."
        else:
            try:
                validate_email(email)
            except Exception:
                errors["email"] = "Invalid email format."

        if data.get("phone_number") and not validate_phone_number(
            data["phone_number"]
        ):
            errors["phone_number"] = "Invalid phone number."

        if errors:
            raise MemberValidationError(errors, code="invalid_member")

        return (
            normalize_text(data.get("first_name", "")),
            normalize_text(data.get("last_name", "")),
            email.lower().strip(),
        )

    @staticmethod
    @transaction.atomic
    def create_member(*, data: dict, created_by: Optional["AbstractUser"]):
        first, last, email = MemberLifecycleService.validate_member_payload(data)

        member = MemberProfile(
            email=email,
            first_name=first,
            last_name=last,
            phone_number=data.get("phone_number"),
            address=data.get("address"),
            status=data["status"],
            employee=data["employee"],
            created_by=created_by,
            updated_by=created_by,
        )
        member.save(user=created_by)

        logger.info("Member created code=%s", member.member_code)
        return member

    @staticmethod
    @transaction.atomic
    def update_member(*, member: MemberProfile, data: dict, updated_by: "AbstractUser"):
        first, last, email = MemberLifecycleService.validate_member_payload(
            data, instance=member
        )

        member.first_name = first
        member.last_name = last
        member.email = email
        member.phone_number = data.get("phone_number", member.phone_number)
        member.address = data.get("address", member.address)
        member.status = data.get("status", member.status)
        member.updated_by = updated_by

        member.save(user=updated_by)
        logger.info("Member updated code=%s", member.member_code)
        return member

    @staticmethod
    @transaction.atomic
    def activate_from_signup(signup_request):
        employee = signup_request.user

        member = MemberProfile.objects.get(employee=employee)
        member.status = MemberStatus.objects.get(code="ACTV")
        member.save(user=signup_request.created_by)

        employee.is_verified = True
        employee.employment_status = EmploymentStatus.objects.get(code="ACTV")
        employee.save(user=signup_request.created_by)

        logger.info("Member activated via signup email=%s", employee.email)
        return member
