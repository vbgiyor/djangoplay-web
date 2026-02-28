import logging

from allauth.account.models import EmailAddress
from allauth.account.views import SignupView
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from mailer.flows.member.verification import send_verification_email_task
from policyengine.components.ssopolicies import setup_role_based_group
from teamcentral.models import (
    Department,
    EmployeeType,
    EmploymentStatus,
    MemberStatus,
    Role,
)
from teamcentral.services import (
    EmployeeLifecycleService,
    MemberLifecycleService,
    OnboardingPolicy,
)
from users.exceptions import EmployeeValidationError
from users.services.identity_signup_flow_service import SignupFlowService
from users.services.identity_verification_token_service import SignupTokenManagerService

logger = logging.getLogger(__name__)


class CustomSignupView(SignupView):

    """
    SSO / Allauth signup orchestration view.

    Responsibilities:
    - Delegate identity creation to users services
    - Delegate HR + membership creation to teamcentral
    - Never touch users.models directly
    """

    template_name = "account/site_pages/login.html"

    @transaction.atomic
    def form_valid(self, form):
        try:
            # -------------------------------------------------
            # 1. Identity creation (users app)
            # -------------------------------------------------
            signup_result = SignupFlowService.handle_allauth_signup(
                request=self.request,
                user=self.user,
                form=form,
            )
            user = signup_result.user

            # -------------------------------------------------
            # 2. Default onboarding policies (teamcentral)
            # -------------------------------------------------
            employee_defaults = OnboardingPolicy.default_employee_defaults()
            member_status = OnboardingPolicy.default_member_status()

            # -------------------------------------------------
            # 3. Employee creation (teamcentral)
            # -------------------------------------------------
            employee = EmployeeLifecycleService.create_employee(
                data={
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    **employee_defaults,
                    "is_active": True,
                    "is_verified": user.is_verified,
                    "hire_date": timezone.now().date(),
                },
                created_by=None,
            )

            employee.groups.add(setup_role_based_group("SSO"))

            # -------------------------------------------------
            # 4. Member creation (teamcentral)
            # -------------------------------------------------
            MemberLifecycleService.create_member(
                data={
                    "email": employee.email,
                    "first_name": employee.first_name,
                    "last_name": employee.last_name,
                    "employee": employee,
                    "status": member_status,
                },
                created_by=employee,
            )

            return super().form_valid(form)

        except Exception:
            logger.exception("SSO signup failed")
            messages.error(
                self.request,
                "An error occurred during signup. Please try again.",
            )
            return redirect(reverse("account_login"))


class ManualVerifyEmailView(View):

    """
    Manual signup + verification initiation view.

    Rules:
    - No direct users.models access
    - All identity operations via services
    - All HR operations via teamcentral
    """

    def post(self, request):
        email = (request.POST.get("email") or "").strip().lower()
        first_name = request.POST.get("first_name", "")
        last_name = request.POST.get("last_name", "")
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")

        if not all([email, first_name, last_name, username, password]):
            messages.error(request, "All fields are required.")
            return redirect(reverse("account_login"))

        with transaction.atomic():
            # -------------------------------------------------
            # Check existing identities (including soft-deleted)
            # -------------------------------------------------
            existing = EmployeeLifecycleService.find_by_email_or_username(
                email=email,
                username=username,
            )
            if existing.get("email_exists"):
                messages.error(request, "This email is already registered.")
                return redirect(reverse("account_login"))

            if existing.get("username_exists"):
                messages.error(request, "This username is already taken.")
                return redirect(reverse("account_login"))

            # -------------------------------------------------
            # Master data
            # -------------------------------------------------
            try:
                dept = Department.objects.get(code="SSO")
                role = Role.objects.get(code="SSO")
                emp_status = EmploymentStatus.objects.get(code="PEND")
                mem_status = MemberStatus.objects.get(code="PEND")
                emp_type = EmployeeType.objects.get(code="SSO")
            except Exception as exc:
                logger.error("ManualSignup: Missing master data", exc_info=exc)
                messages.error(request, "Required master configuration missing.")
                return redirect(reverse("account_login"))

            # -------------------------------------------------
            # Employee creation (teamcentral)
            # -------------------------------------------------
            employee_data = {
                "email": email,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "sso_provider": "EMAIL",
                "sso_id": "",
                "is_active": True,
                "is_verified": False,
                "department": dept,
                "role": role,
                "employment_status": emp_status,
                "employee_type": emp_type,
                "is_superuser": False,
                "hire_date": timezone.now().date(),
            }

            try:
                employee = EmployeeLifecycleService.create_employee(
                    data=employee_data,
                    created_by=None,
                )
            except EmployeeValidationError as exc:
                messages.error(request, str(exc))
                return redirect(reverse("account_login"))

            employee.set_password(password)
            employee.save()

            employee.groups.add(setup_role_based_group("SSO"))

            # -------------------------------------------------
            # Member creation
            # -------------------------------------------------
            member = MemberLifecycleService.create_member(
                data={
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "employee": employee,
                    "status": mem_status,
                },
                created_by=employee,
            )

            # -------------------------------------------------
            # EmailAddress (allauth)
            # -------------------------------------------------
            EmailAddress.objects.update_or_create(
                user=employee,
                email=email,
                defaults={"verified": False, "primary": True},
            )

            # -------------------------------------------------
            # Signup token + verification email
            # -------------------------------------------------
            signup_request, status = SignupTokenManagerService.create_for_user(
                user=employee,
                request=request,
                flow="signup_request",
            )

            if status == "ok":
                send_verification_email_task.delay(member.id)

            messages.info(
                request,
                "Signup successful. Check your email to verify your account.",
            )
            return redirect(reverse("account_login") + "?email_sent=true")
