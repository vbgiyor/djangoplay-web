import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views import View
from users.exceptions import EmployeeValidationError, MemberValidationError
from users.services.signup_flow import SignupFlowService
from utilities.commons.helpers import employee_state_by_email
from utilities.services.links.resend import build_resend_verification_url

logger = logging.getLogger(__name__)


class ManualSignupView(View):

    """
    Handles manual (email/password) signup.
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
            _, _, status = SignupFlowService.handle_manual_signup(
                data=data,
                request=request,
            )

        # -------------------------------------------------
        # Business rule violations (preferred path)
        # -------------------------------------------------
        except MemberValidationError as exc:
            logger.info("Manual signup blocked (member rule): %s", exc)

            for _, msg in exc.message_dict.items():
                messages.error(request, mark_safe(msg))

            return redirect(reverse("account_login"))

        # -------------------------------------------------
        # Identity / DB conflicts (fallback path)
        # -------------------------------------------------
        except EmployeeValidationError as exc:
            email = data.get("email")
            state, _ = employee_state_by_email(email)

            logger.info(
                "Manual signup blocked (employee rule): %s | state=%s",
                exc,
                state,
            )

            if state == "unverified":
                resend_url = build_resend_verification_url(email)

                msg = (
                    "An account already exists with this email address but is not yet verified. "
                    "Please activate your account using the link sent to your email, or request a new verification email "
                )
                msg = mark_safe(f'{msg}<a href="{resend_url}">here</a>.')

                messages.error(request, msg)

            else:
                login_url = reverse("account_login")
                msg = (
                    "An account already exists with this email address. "
                    "Please sign in using your existing account."
                )
                msg = mark_safe(f'{msg} <a href="{login_url}">Sign in</a>.')

                messages.error(request, msg)

            return redirect(reverse("account_login"))

        # -------------------------------------------------
        # True system failure
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
        if status == "ok":
            messages.success(
                request,
                "Signup successful. Please check your email to verify your account.",
            )
        else:
            messages.error(
                request,
                "Too many verification attempts. Please try again later.",
            )

        return redirect(reverse("account_login"))
