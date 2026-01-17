import logging

from allauth.account.models import EmailAddress
from allauth.account.views import SignupView
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from drf_spectacular.utils import extend_schema
from mailer.flows.member.verification import send_verification_email_task
from policyengine.components.ssopolicies import setup_role_based_group
from users.exceptions import EmployeeValidationError
from users.models import (
    Department,
    Employee,
    EmployeeType,
    EmploymentStatus,
    MemberStatus,
    Role,
)
from users.services.employee import EmployeeService
from users.services.member import MemberService
from users.services.signup_flow import SignupFlowService
from users.services.signup_token_manager import SignupTokenManagerService

logger = logging.getLogger(__name__)


@extend_schema(tags=["Platform Member: Member Signup"])
class CustomSignupView(SignupView):
    template_name = "account/site_pages/signup.html"

    def form_valid(self, form):
        try:
            result = SignupFlowService.handle_allauth_signup(
                request=self.request,
                user=self.user,
                form=form,
            )
            self.user = result.user
            return super().form_valid(form)
        except Exception:
            logger.exception("Allauth signup failed")
            messages.error(
                self.request,
                "An error occurred during signup. Please try again.",
            )
            return self.form_invalid(form)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["departments"] = Department.all_objects.filter(
            deleted_at__isnull=True,
            is_active=True,
        )
        return context


class ManualVerifyEmailView(View):
    def post(self, request):
        email = (request.POST.get("email") or "").strip().lower()
        first_name = request.POST.get("first_name", "")
        last_name = request.POST.get("last_name", "")
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")

        if not email or not first_name or not last_name or not username or not password:
            messages.error(request, "All fields are required.")
            return redirect(reverse("account_login"))

        with transaction.atomic():

            # Check all states (including soft-deleted)
            existing_qs = Employee.all_objects.filter(
                Q(email__iexact=email) | Q(username__iexact=username)
            )
            if existing_qs.filter(email__iexact=email).exists():
                messages.error(request, "This email is already registered.")
                return redirect(reverse("account_login"))

            if existing_qs.filter(username__iexact=username).exists():
                messages.error(request, "This username is already taken.")
                return redirect(reverse("account_login"))

            # Master data
            try:
                dept = Department.objects.get(code="SSO")
                role = Role.objects.get(code="SSO")
                emp_status = EmploymentStatus.objects.get(code="PEND")
                mem_status = MemberStatus.objects.get(code="PEND")
                emp_type = EmployeeType.objects.get(code="SSO")
            except Exception as e:
                messages.error(request, "Required master configuration missing.")
                logger.error("ManualSignup: Missing master data %s", e)
                return redirect(reverse("account_login"))

            # Employee
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
                employee = EmployeeService.create_employee(employee_data, created_by=None)
            except EmployeeValidationError as e:
                messages.error(request, str(e))
                return redirect(reverse("account_login"))

            employee.set_password(password)
            employee.save()

            # Group
            employee.groups.add(setup_role_based_group("SSO"))

            # Member
            member_data = {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "employee": employee,
                "status": mem_status,
            }
            member = MemberService.create_member(member_data, created_by=employee)

            EmailAddress.objects.update_or_create(
                user=employee,
                email=email,
                defaults={"verified": False, "primary": True},
            )

            # Use unified token service
            signup_request, status = SignupTokenManagerService.create_for_user(
                user=employee,
                request=request,
            )

            if status == "created":
                send_verification_email_task.delay(member.id)

            messages.info(request, "Signup successful. Check your email to verify your account.")
            return redirect(reverse("account_login") + "?email_sent=true")
