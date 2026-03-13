import logging
from dataclasses import dataclass

from allauth.account.models import EmailAddress
from allauth.core.exceptions import ImmediateHttpResponse
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from policyengine.components.ssopolicies import setup_role_based_group
from teamcentral.models import (
    Department,
    EmployeeType,
    EmploymentStatus,
    MemberProfile,
    MemberStatus,
    Role,
)
from teamcentral.services import EmployeeLifecycleService, MemberLifecycleService

from users.models import Employee

logger = logging.getLogger(__name__)


@dataclass
class SSOOnboardingResult:

    """
    Encapsulates the outcome of a social login pre-processing step.

    If `response` is non-None, the caller (adapter) should short-circuit
    and return that response (typically a redirect).
    """

    response: HttpResponse | None = None


class SSOOnboardingService:

    """
    Service layer for handling SSO / social login onboarding logic.

    This is called by CustomSocialAccountAdapter.pre_social_login
    so that the adapter itself stays thin and focused on allauth glue.
    """

    @staticmethod
    def _get_provider_code(provider: str) -> str:
        provider = (provider or "").lower()
        if provider == "google":
            return "GOOGLE"
        if provider == "apple":
            return "APPLE"
        return "EMAIL"

    @staticmethod
    def _get_master_defaults():
        """
        Fetch master data needed for SSO-created employees & members.
        """
        try:
            default_dept = Department.objects.get(code="SSO")
            default_role = Role.objects.get(code="SSO")
            default_status = EmploymentStatus.objects.get(code="ACTV")
            default_member_status = MemberStatus.objects.get(code="ACTV")
            default_type = EmployeeType.objects.get(code="SSO")
        except Exception as e:
            logger.error(f"Required master data not found for SSO onboarding: {e}")
            raise
        return {
            "department": default_dept,
            "role": default_role,
            "employment_status": default_status,
            "member_status": default_member_status,
            "employee_type": default_type,
        }

    @staticmethod
    def _build_username_from_email(email: str) -> str:
        base_username = email.split("@")[0][:30]
        username = base_username
        counter = 1
        while Employee.objects.filter(
            username__iexact=username,
            deleted_at__isnull=True
        ).exists():
            username = f"{base_username}{counter}"
            counter += 1
        return username

    @staticmethod
    @transaction.atomic
    def _link_existing_employee_by_sso_id(
        request: HttpRequest,
        sso_id: str,
        provider_code: str,
        email: str,
        sociallogin,
    ) -> bool:
        """
        Return True if an existing employee was found and linked, else False.
        """
        try:
            employee = Employee.objects.get(
                sso_id=sso_id,
                sso_provider=provider_code,
                is_active=True,
                deleted_at__isnull=True,
            )
        except Employee.DoesNotExist:
            return False

        logger.info(
            "SSOOnboardingService: Found existing Employee for SSO ID %s: %s",
            sso_id,
            employee.employee_code,
        )

        sociallogin.account.user = employee
        sociallogin.account.save()
        sociallogin.user = employee

        # Optional: keep direct login here
        auth_login(
            request,
            employee,
            backend="django.contrib.auth.backends.ModelBackend",
        )

        return True


    @staticmethod
    @transaction.atomic
    def _link_existing_employee_by_email(
        request: HttpRequest,
        sso_id: str,
        provider_code: str,
        email: str,
        sociallogin,
    ) -> bool:
        """
        Return True if an existing employee was found by email and linked, else False.
        """
        try:
            employee = Employee.objects.get(
                email__iexact=email,
                is_active=True,
                deleted_at__isnull=True,
            )
        except Employee.DoesNotExist:
            return False

        logger.info(
            "SSOOnboardingService: Found existing Employee with email %s, linking to SSO ID %s",
            email,
            sso_id,
        )

        employee.sso_id = sso_id
        employee.sso_provider = provider_code
        employee.save(user=employee)

        sso_group = setup_role_based_group("SSO")
        employee.groups.add(sso_group)

        sociallogin.account.user = employee
        sociallogin.account.save()
        sociallogin.user = employee

        # Optional: keep direct login here
        auth_login(
            request,
            employee,
            backend="django.contrib.auth.backends.ModelBackend",
        )

        return True


    @staticmethod
    @transaction.atomic
    def _create_employee_and_member_from_sso(
        request: HttpRequest,
        sso_id: str,
        provider_code: str,
        email: str,
        sociallogin,
    ) -> None:
        # 1) Master data
        try:
            defaults = SSOOnboardingService._get_master_defaults()
        except Exception:
            messages.error(
                request,
                "Required master data not found. Please contact support.",
            )
            # Hard failure → explicit redirect
            raise ImmediateHttpResponse(HttpResponseRedirect(reverse("account_login")))

        # 2) Username & Employee
        username = SSOOnboardingService._build_username_from_email(email)
        employee_data = {
            "email": email,
            "username": username,
            "first_name": sociallogin.account.extra_data.get("given_name", ""),
            "last_name": sociallogin.account.extra_data.get("family_name", ""),
            "sso_id": sso_id,
            "sso_provider": provider_code,
            "is_active": True,
            "is_verified": True,
            "department": defaults["department"],
            "role": defaults["role"],
            "employment_status": defaults["employment_status"],
            "employee_type": defaults["employee_type"],
            "hire_date": timezone.now().date(),
            "is_superuser": email == "redstar@djangoplay.org",
        }
        employee = EmployeeLifecycleService.create_employee(data=employee_data, created_by=None)

        # Add SSO group
        sso_group = setup_role_based_group("SSO")
        employee.groups.add(sso_group)

        # 3) Member
        try:
            member = MemberProfile.objects.get(
                employee=employee,
                deleted_at__isnull=True,
            )
        except MemberProfile.DoesNotExist:
            member_data = {
                "email": employee.email,
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "employee": employee,
                "status": defaults["member_status"],
            }
            member = MemberLifecycleService.create_member(member_data, created_by=employee)

        # 4) EmailAddress
        EmailAddress.objects.update_or_create(
            user=employee,
            email=email,
            defaults={"verified": True, "primary": True},
        )

        # 5) Welcome email (async best-effort)
        from mailer.flows.member.signup import send_successful_signup_email_task
        try:
            send_successful_signup_email_task.delay(member.id)
            request.session["first_time_signup"] = True
        except Exception as e:
            logger.error(
                "SSOOnboardingService: Failed to queue signup email to %s: %s",
                email,
                e,
            )

        # 6) Final login
        sociallogin.account.user = employee
        sociallogin.account.save()
        sociallogin.user = employee

        auth_login(
            request,
            employee,
            backend="django.contrib.auth.backends.ModelBackend",
        )


    # ------------------------------------------------------------------ #
    # Public entrypoint called by CustomSocialAccountAdapter
    # ------------------------------------------------------------------ #
    @staticmethod
    def handle_pre_social_login(request: HttpRequest, sociallogin) -> SSOOnboardingResult:
        """
        Main orchestration method.

        Returns SSOOnboardingResult with an HttpResponse (redirect)
        only when the flow should be short-circuited (errors / special onboarding).
        """
        sso_id = sociallogin.account.uid
        provider = sociallogin.account.provider
        email = (sociallogin.account.extra_data.get("email", "") or "").lower().strip()

        # Dormant but useful logger to get metadata provided by social account provider
        # logger.info(
        #     "SSO extra_data received from %s: %s",
        #     provider,
        #     sociallogin.account.extra_data,
        # )

        if not email:
            logger.warning(
                "SSO login blocked: provider=%s uid=%s (no email returned)",
                provider,
                sso_id,
            )
            messages.error(
                request,
                "Your social account did not provide an email address. "
                "Please use an account with a verified email or sign up manually.",
            )
            return SSOOnboardingResult(
                response=HttpResponseRedirect(reverse("social_login_error"))
            )

        provider_code = SSOOnboardingService._get_provider_code(provider)

        try:
            # 1) Existing employee by SSO ID
            if SSOOnboardingService._link_existing_employee_by_sso_id(
                request=request,
                sso_id=sso_id,
                provider_code=provider_code,
                email=email,
                sociallogin=sociallogin,
            ):
                # handled successfully → let allauth continue, adapter decides redirect
                return SSOOnboardingResult(response=None)

            # 2) Existing employee by email
            if SSOOnboardingService._link_existing_employee_by_email(
                request=request,
                sso_id=sso_id,
                provider_code=provider_code,
                email=email,
                sociallogin=sociallogin,
            ):
                return SSOOnboardingResult(response=None)

            # 3) Brand-new employee + member
            SSOOnboardingService._create_employee_and_member_from_sso(
                request=request,
                sso_id=sso_id,
                provider_code=provider_code,
                email=email,
                sociallogin=sociallogin,
            )
            return SSOOnboardingResult(response=None)

        except ImmediateHttpResponse as ih:
            # Pass through explicit early-exit redirects (rare cases)
            return SSOOnboardingResult(response=ih.response)

        except Exception as e:
            logger.exception(
                "SSOOnboardingService: Unexpected error during social login for %s: %s",
                email,
                e,
            )
            messages.error(
                request,
                "An error occurred during social login. Please try again.",
            )
            return SSOOnboardingResult(
                response=HttpResponseRedirect(reverse("account_login"))
            )

