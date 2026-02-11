import logging

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views import View
from mailer.flows.member.verification import send_manual_verification_email_task
from mailer.links.resend import build_resend_verification_url
from teamcentral.services.member_lifecycle_service import MemberLifecycleService
from teamcentral.services.onboarding_policy import OnboardingPolicy
from users.exceptions import EmployeeValidationError, MemberValidationError
from users.services.identity_signup_flow_service import SignupFlowService
from utilities.commons.helpers import employee_state_by_email

logger = logging.getLogger(__name__)


class ManualSignupView(View):

    """
    Manual email/password signup.

    Orchestration responsibilities:
    - Identity creation (users)
    - HR defaults resolution (teamcentral policy)
    - HR enrichment of identity employee
    - Member creation
    """

    def post(self, request):
        data = {
            "email": (request.POST.get("email") or "").strip().lower(),
            "first_name": request.POST.get("first_name", "").strip(),
            "last_name": request.POST.get("last_name", "").strip(),
            "username": request.POST.get("username", "").strip(),
            "password": request.POST.get("password", ""),
        }

        if not all(data.values()):
            messages.error(request, "All fields are required.")
            return redirect(reverse("account_login"))

        try:
            # -------------------------------------------------
            # 1. HR defaults (policy owns meaning)
            # -------------------------------------------------
            employee_defaults = OnboardingPolicy.default_employee_defaults()
            member_status = OnboardingPolicy.default_member_status()

            # -------------------------------------------------
            # 2. Identity creation (creates Employee row)
            # -------------------------------------------------
            signup_result = SignupFlowService.handle_manual_signup(
                data=data,
                request=request,
                hr_defaults=employee_defaults,
            )
            employee = signup_result.user

            # -------------------------------------------------
            # 3. Member creation (HR lifecycle)
            # -------------------------------------------------
            member = MemberLifecycleService.create_member(
                data={
                    "email": employee.email,
                    "first_name": employee.first_name,
                    "last_name": employee.last_name,
                    "employee": employee,
                    "status": member_status,
                },
                created_by=employee,
            )

            from mailer.flows.member import send_successful_signup_email_task

            transaction.on_commit(lambda: send_successful_signup_email_task.delay(member.id))


        # -------------------------------------------------
        # Business rule violations
        # -------------------------------------------------
        except MemberValidationError as exc:
            for _, msg in exc.message_dict.items():
                messages.error(request, mark_safe(msg))
            return redirect(reverse("account_login"))

        except EmployeeValidationError:
            email = data["email"]
            state, _ = employee_state_by_email(email)

            if state == "unverified":
                resend_url = build_resend_verification_url(email)
                msg = (
                    "An account already exists but is not verified. "
                    f'<a href="{resend_url}">Resend verification email</a>.'
                )
                messages.error(request, mark_safe(msg))
            else:
                login_url = reverse("account_login")
                msg = (
                    "An account already exists. "
                    f'<a href="{login_url}">Sign in</a>.'
                )
                messages.error(request, mark_safe(msg))

            return redirect(reverse("account_login"))

        # -------------------------------------------------
        # System failure
        # -------------------------------------------------
        except Exception:
            logger.exception("Manual signup failed unexpectedly")
            messages.error(
                request,
                "Unable to complete signup. Please try again later.",
            )
            return redirect(reverse("account_login"))

        # -------------------------------------------------
        # Success
        # -------------------------------------------------
        messages.success(
            request,
            "Signup successful. Please check your email to verify your account.",
        )
        return redirect(reverse("account_login"))
