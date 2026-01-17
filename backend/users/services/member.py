import logging
from typing import Optional

from django.conf import settings
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from utilities.utils.general.normalize_text import normalize_text
from utilities.utils.locations.phone_number_validations import validate_phone_number

from users.constants import (
    DEPARTMENT_CODES,
    EMPLOYEE_TYPE_CODES,
    EMPLOYMENT_STATUS_CODES,
    MEMBER_STATUS_CODES,
    ROLE_CODES,
    SSO_PROVIDER_CODES,
)
from users.exceptions import MemberValidationError
from users.models import (
    Department,
    Employee,
    EmployeeType,
    EmploymentStatus,
    Member,
    MemberStatus,
    Role,
    SignUpRequest,
)

logger = logging.getLogger(__name__)


class MemberService:

    """Service layer for Member (external users) and related operations."""

    # ==============================
    # VALIDATION & CRUD
    # ==============================

    @staticmethod
    def validate_member_data(data, instance: Optional[Member] = None):
        """
        Validate member data for create/update.
        Returns normalized (first_name, last_name, email) if valid.
        Raises MemberValidationError on error.
        """
        errors = {}

        if not data.get("email"):
            errors["email"] = "Email is required."

        try:
            validate_email(data.get("email"))
        except Exception:
            errors["email"] = "Invalid email format."

        if data.get("phone_number") and not validate_phone_number(
            data.get("phone_number")
        ):
            errors["phone_number"] = "Invalid phone number format."

        if data.get("email") and Member.objects.filter(
            email=data.get("email"),
            deleted_at__isnull=True,
        ).exclude(pk=instance.pk if instance else None).exists():
            errors["email"] = "Email already in use."

        if not data.get("employee") or not isinstance(data["employee"], Employee):
            errors["employee"] = "Valid Employee instance is required."

        if not data.get("status") or not isinstance(data["status"], MemberStatus):
            errors["status"] = "Valid MemberStatus instance is required."

        if errors:
            logger.error("Validation failed for member data: %s", errors)
            raise MemberValidationError(errors, code="invalid_fields")

        return (
            normalize_text(data.get("first_name", "")),
            normalize_text(data.get("last_name", "")),  # fixed typo
            normalize_text(data.get("email", "")),
        )

    @staticmethod
    @transaction.atomic
    def create_member(data, created_by: Optional[Employee]):
        logger.info(
            "Creating member: email=%s, created_by=%s",
            data.get("email"),
            created_by,
        )
        first_name, last_name, email = MemberService.validate_member_data(data)

        try:
            employee = data["employee"]
            if not employee.is_active:
                logger.error(
                    "Cannot create member for inactive employee: %s",
                    employee.employee_code,
                )
                raise MemberValidationError(
                    "Cannot create member for inactive employee",
                    code="invalid_employee",
                    details={"employee_code": employee.employee_code},
                )

            member = Member(
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=data.get("phone_number"),
                address=data.get("address"),
                status=data["status"],
                employee=employee,
                created_by=created_by,
                updated_by=created_by,
            )
            member.save(user=created_by)
            logger.info(
                "Member created: %s, linked to Employee: %s",
                member.member_code,
                employee.employee_code,
            )

            if not Member.objects.filter(
                member_code=member.member_code,
                deleted_at__isnull=True,
            ).exists():
                logger.error(
                    "Failed to persist Member after save: %s",
                    member.member_code,
                )
                raise MemberValidationError(
                    "Failed to save member record",
                    code="member_save_error",
                )

            return member

        except MemberValidationError:
            raise
        except Exception as e:
            logger.error(
                "Validation error creating member for email %s: %s",
                email,
                e,
            )
            raise MemberValidationError(
                f"Failed to create member: {str(e)}",
                code="member_creation_failed",
                details={"error": str(e)},
            )

    @staticmethod
    @transaction.atomic
    def update_member(member: Member, data, updated_by: Employee):
        logger.info(
            "Updating member: %s, updated_by=%s",
            member.member_code,
            updated_by,
        )
        first_name, last_name, email = MemberService.validate_member_data(
            data, member
        )

        for field, value in data.items():
            if field == "first_name":
                value = first_name
            elif field == "last_name":
                value = last_name
            elif field == "email":
                value = email

            if field in [
                "first_name",
                "last_name",
                "email",
                "phone_number",
                "address",
                "status",
            ]:
                setattr(member, field, value)

        member.updated_by = updated_by
        member.address_display = str(member.address) if member.address else "No address"

        try:
            employee = member.employee
            employee.email = email
            employee.first_name = first_name
            employee.last_name = last_name
            employee.save(user=updated_by)

            member.save(user=updated_by)
            logger.info(
                "Member updated: %s, Employee updated: %s",
                member.member_code,
                employee.employee_code,
            )
            return member
        except Exception as e:
            logger.error(
                "Failed to update member %s: %s",
                member.member_code,
                e,
            )
            raise MemberValidationError(
                f"Failed to update member: {str(e)}",
                code="member_update_failed",
                details={"error": str(e)},
            )

    @staticmethod
    @transaction.atomic
    def create_signup_request(data, created_by: Employee):
        """
        Member + Employee creation via signup (non-SSO) flow.
        """
        logger.info(
            "Creating signup request: email=%s, created_by=%s",
            data.get("email"),
            created_by,
        )

        if data.get("email") == "redstar@djangoplay.com":
            logger.info("Skipping signup request for redstar@djangoplay.com")
            return None

        first_name, last_name, email = MemberService.validate_member_data(data)

        try:
            default_dept = Department.objects.get(
                code=DEPARTMENT_CODES["SSO"],
            )
            default_role = Role.objects.get(code=ROLE_CODES["SSO"])
            default_status = EmploymentStatus.objects.get(
                code=EMPLOYMENT_STATUS_CODES["PEND"],
            )
            default_type = EmployeeType.objects.get(
                code=EMPLOYEE_TYPE_CODES["SSO"],
            )
            default_member_status = MemberStatus.objects.get(
                code=MEMBER_STATUS_CODES["PEND"],
            )

            employee = Employee.objects.create_user(
                username=data.get("username", email.split("@")[0][:30]),
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=data.get("password"),
                department=default_dept,
                role=default_role,
                employment_status=default_status,
                employee_type=default_type,
                sso_provider=data.get("sso_provider", SSO_PROVIDER_CODES["EMAIL"]),
                sso_id=data.get("sso_id", ""),
                is_verified=False,
                created_by=created_by,
            )

            member = Member(
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=data.get("phone_number"),
                address=data.get("address"),
                status=default_member_status,
                employee=employee,
                created_by=created_by,
                updated_by=created_by,
            )
            member.save(user=created_by)

            expires_at = timezone.now() + timezone.timedelta(
                days=settings.LINK_EXPIRY_DAYS["email_verification"]
            )
            signup_request = SignUpRequest(
                user=employee,
                sso_provider=data.get("sso_provider", SSO_PROVIDER_CODES["EMAIL"]),
                sso_id=data.get("sso_id", ""),
                expires_at=expires_at,
                created_by=created_by,
            )
            signup_request.save(user=created_by)

            from mailer.flows.member.verification import send_manual_verification_email_task
            # Async verification email via Celery
            send_manual_verification_email_task.delay(
                member.id,
                data.get("username"),
                first_name,
                last_name,
            )

            logger.info(
                "Signup request created for: %s",
                signup_request.user.email,
            )
            return signup_request

        except Exception as e:
            logger.error("Failed to create signup request: %s", e)
            raise MemberValidationError(
                f"Failed to create signup request: {str(e)}",
                code="signup_request_failed",
                details={"error": str(e)},
            )

    @staticmethod
    @transaction.atomic
    def create_member_from_signup(signup_request: SignUpRequest) -> Member:
        """
        Activate member + employee from SignUpRequest.
        """
        logger.info(
            "Activating member from signup: email=%s",
            signup_request.user.email,
        )
        try:
            member = Member.objects.get(employee=signup_request.user)
            member.status = MemberStatus.objects.get(
                code=MEMBER_STATUS_CODES["ACTV"],
            )
            member.save(user=signup_request.created_by)

            employee = signup_request.user
            employee.is_verified = True
            employee.employment_status = EmploymentStatus.objects.get(
                code=EMPLOYMENT_STATUS_CODES["ACTV"],
            )
            employee.save(user=signup_request.created_by)

            logger.info("Member activated: %s", member.member_code)
            return member

        except Exception as e:
            logger.error(
                "Failed to activate member from signup %s: %s",
                signup_request.user.email,
                e,
            )
            raise MemberValidationError(
                f"Failed to activate member from signup: {str(e)}",
                code="member_activation_failed",
                details={"error": str(e)},
            )

    @staticmethod
    def is_duplicate_email(email: str, exclude_pk: Optional[int] = None) -> bool:
        """Check if email already exists for a non-deleted Member."""
        return Member.objects.filter(
            email__iexact=email,
            deleted_at__isnull=True,
        ).exclude(pk=exclude_pk).exists()
