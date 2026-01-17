from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from users.exceptions import MemberValidationError
from utilities.commons.helpers import employee_state_by_email

from mailer.links.resend import build_resend_verification_url


def enforce_email_signup_rules(email: str) -> None:
    """
    Enforce signup rules for an email.

    Raises MemberValidationError if signup must be blocked.
    """
    if not email:
        return

    state, emp = employee_state_by_email(email)  # <-- FIXED HERE

    # ---------------------------------------------------------
    # Case 1: Email already exists AND is verified
    # ---------------------------------------------------------
    if state == "active":
        login_url = reverse("account_login")

        msg = _(
            "An account already exists with this email address. "
            "Please sign in using your existing account."
        )
        msg = mark_safe(f'{msg} <a href="{login_url}">Sign in</a>.')

        raise MemberValidationError(
            {"email": msg},
            code="email_already_registered",
        )

    # ---------------------------------------------------------
    # Case 2: Email exists but is NOT verified
    # ---------------------------------------------------------
    if state == "unverified":
        resend_url = build_resend_verification_url(email)

        msg = _(
            "An account already exists with this email address but is not yet verified. "
            "Please activate your account using the link sent to your email, or request a new verification email "
        )
        msg = mark_safe(f'{msg}<a href="{resend_url}">here</a>.')

        raise MemberValidationError(
            {"email": msg},
            code="email_unverified",
        )

    # All other states → allowed


def handle_unverified_email(
    *,
    request,
    email: str,
    context: str,  # "login" | "support"
):
    """
    Runtime UX handler for unverified emails.

    Used ONLY in:
      - Login flow
      - Support submission

    Does NOT affect signup validation logic.
    """
    if not email:
        return None

    state, emp = employee_state_by_email(email)

    if state != "unverified":
        return None

    resend_url = build_resend_verification_url(email)

    if context == "login":
        msg = _("Email verification pending. Please verify your email.")
        msg = mark_safe(f'{msg} <a href="{resend_url}">Resend activation link</a>.')
    else:
        msg = _(
            "Your account is not verified. Please activate your account using the link sent to your email, "
            "or request a new verification email "
        )
        msg = mark_safe(f'{msg}<a href="{resend_url}">here</a>.')

    messages.error(request, msg)

    return redirect(
        reverse("console_dashboard")
        if request.user.is_authenticated
        else reverse("account_login")
    )
