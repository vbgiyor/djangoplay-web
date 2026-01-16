import logging
from dataclasses import dataclass
from typing import Any, Optional, Type

from allauth.account.models import EmailAddress
from allauth.account.utils import user_email, user_field
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from policyengine.components.ssopolicies import setup_role_based_group
from utilities.services.email.resend_verification import *
from utilities.services.email.unverified_guard import enforce_email_signup_rules

from users.models import *
from users.services import EmployeeService, MemberService
from users.services.signup_token_manager import SignupTokenManagerService

logger = logging.getLogger(__name__)
UserModel = get_user_model()


@dataclass
class SignupSaveResult:
    user: Optional[Type[Any]] = None


class SignupFlowService:

    @staticmethod
    def _get_signup_defaults():
        try:
            return {
                "department": Department.objects.get(code="SSO"),
                "role": Role.objects.get(code="SSO"),
                "employment_status": EmploymentStatus.objects.get(code="PEND"),
                "employee_type": EmployeeType.objects.get(code="SSO"),
                "member_status": MemberStatus.objects.get(code="PEND"),
            }
        except Exception as e:
            logger.error(f"Required signup master data missing: {e}")
            raise ValidationError(f"Required master data not found: {e}")

    # ------------------------------------------------------------------
    # MANUAL SIGNUP (EMAIL / PASSWORD)
    # ------------------------------------------------------------------
    @staticmethod
    def handle_manual_signup(*, data: dict, request):
        """
        Manual email/password signup.

        Responsibilities:
        - Create Employee
        - Create Member
        - Send welcome email
        - Send verification email (via resend service)
        """
        # -------------------------------------------------
        # HARD STOP: email state enforcement
        # -------------------------------------------------
        email = data.get("email")
        enforce_email_signup_rules(email)

        # -----------------------
        # Master data
        # -----------------------
        dept = Department.objects.get(code="SSO")
        role = Role.objects.get(code="SSO")
        emp_status = EmploymentStatus.objects.get(code="PEND")
        emp_type = EmployeeType.objects.get(code="SSO")
        mem_status = MemberStatus.objects.get(code="PEND")

        # -----------------------
        # Employee
        # -----------------------
        employee = EmployeeService.create_employee(
            {
                "email": data["email"].lower(),
                "username": data["username"],
                "first_name": data["first_name"],
                "last_name": data["last_name"],
                "sso_provider": "EMAIL",
                "sso_id": "",
                "is_active": True,
                "is_verified": False,
                "department": dept,
                "role": role,
                "employment_status": emp_status,
                "employee_type": emp_type,
                "hire_date": timezone.now().date(),
                "is_superuser": False,
            },
            created_by=None,
        )

        employee.set_password(data["password"])
        employee.save()

        employee.groups.add(setup_role_based_group("SSO"))

        # -----------------------
        # Member
        # -----------------------
        member = MemberService.create_member(
            {
                "email": employee.email,
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "employee": employee,
                "status": mem_status,
            },
            created_by=employee,
        )

        # -----------------------
        # Welcome email
        # -----------------------
        from utilities.services.email.member_notifications import send_successful_signup_email_task, send_verification_email_task
        try:
            send_successful_signup_email_task.delay(member.id)
        except Exception:
            logger.exception(
                "Manual signup: failed to queue welcome email for %s",
                employee.email,
            )

        return employee, member, "ok"


    @staticmethod
    @transaction.atomic
    def handle_allauth_signup(request, user, form, commit=True):
        data = form.cleaned_data
        defaults = SignupFlowService._get_signup_defaults()

        # Set base user fields
        user_email(user, data.get("email", "").lower())
        user_field(user, "first_name", data.get("first_name", ""))
        user_field(user, "last_name", data.get("last_name", ""))
        user.role = defaults["role"]
        user.employment_status = defaults["employment_status"]
        user.employee_type = defaults["employee_type"]
        user.is_staff = False
        user.is_superuser = (user.username == "redstar")
        user.is_verified = (user.username == "redstar")
        user.sso_provider = "EMAIL"
        user.preferences = {"newsletters": True, "offers": True, "updates": True}

        # If department provided in form
        dept_id = data.get("department")
        if dept_id:
            try:
                user.department = Department.objects.get(id=dept_id)
            except Department.DoesNotExist:
                raise ValidationError(f"Department id '{dept_id}' not found")
        else:
            user.department = defaults["department"]

        # Redstar override
        if user.username == "redstar":
            user.employment_status = EmploymentStatus.objects.get(code="ACTV")

        if commit:
            user.save()

        # EmailAddress (one place only)
        EmailAddress.objects.update_or_create(
            user=user,
            email=user.email.lower(),
            defaults={"verified": user.is_verified, "primary": True},
        )

        # Member creation
        member = Member.objects.filter(employee=user).first()
        if not member:
            member = MemberService.create_member(
                {
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "employee": user,
                    "status": (
                        MemberStatus.objects.get(code="ACTV")
                        if user.username == "redstar"
                        else defaults["member_status"]
                    ),
                },
                created_by=user,
            )
            from utilities.services.email.member_notifications import send_successful_signup_email_task, send_verification_email_task
            send_successful_signup_email_task.delay(member.id)

        # For email signups (non-redstar): create token
        if user.username != "redstar":
            signup_request, status = SignupTokenManagerService.create_for_user(
                user=user,
                request=request,
            )
            if status == "ok":
                send_verification_email_task.delay(member.id)


        return SignupSaveResult(user=user)

    # ------------------------------------------------------------------ #
    # Confirmation email → activate Employee + Member
    # ------------------------------------------------------------------ #
    @staticmethod
    @transaction.atomic
    def handle_email_confirmation(email_address) -> None:
        """
        Called by CustomAccountAdapter.confirm_email to apply your domain
        rules after the email address is marked as verified.
        """
        try:
            employee = Employee.objects.get(email=email_address.email)
        except Employee.DoesNotExist:
            logger.info(
                "SignupFlowService.handle_email_confirmation: No Employee found for %s",
                email_address.email,
            )
            return

        # Mark employee as verified + active
        try:
            active_status = EmploymentStatus.objects.get(code="ACTV")
        except EmploymentStatus.DoesNotExist:
            logger.warning("EmploymentStatus 'ACTV' not found during confirmation")
            active_status = None

        employee.is_verified = True
        if active_status:
            employee.employment_status = active_status
        employee.save()

        # Member status → ACTV if exists
        try:
            member = Member.objects.get(employee=employee)
        except Member.DoesNotExist:
            return

        try:
            active_member_status = MemberStatus.objects.get(code="ACTV")
            member.status = active_member_status
            member.save()
        except MemberStatus.DoesNotExist:
            logger.warning("MemberStatus 'ACTV' not found during confirmation")
            # still keep going
