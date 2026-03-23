import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import get_request_param
from allauth.core.exceptions import ImmediateHttpResponse
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from mailer.engine.engine import EmailEngine
from mailer.engine.verification_guard import handle_unverified_email

from users.adapters.base import BaseAdapter
from users.services.identity_login_policy_service import UnifiedLoginService
from users.services.identity_signup_flow_service import SignupFlowService

logger = logging.getLogger(__name__)


class CustomAccountAdapter(BaseAdapter, DefaultAccountAdapter):

    """
    ============================================================================
    CUSTOM ACCOUNT ADAPTER (THIN, SERVICE-DRIVEN)
    ----------------------------------------------------------------------------
    This adapter contains no domain logic.

    It delegates:

      • signup → SignupFlowService.handle_allauth_signup
      • confirmation → SignupFlowService.handle_email_confirmation
      • login validation → UnifiedLoginService.validate_user
      • email sending → EmailEngine.send

    This keeps the adapter focused on Allauth "glue" only, improving
    maintainability and making business logic testable independently.

    Password reset logic is no longer implemented here (Option A).
    ============================================================================
    """

    @property
    def email_engine(self):
        """
        Lazily instantiate EmailEngine.
        Safe for Celery + request-less contexts.
        """
        return EmailEngine()

    # ------------------------------------------------------------------ #
    # send_mail → thin delegation to EmailEngine
    # ------------------------------------------------------------------ #
    def send_mail(self, template_prefix, email, context):
        """
        Override Allauth's send_mail to use our EmailEngine.

        template_prefix examples:
            "account_signup"
            "email_verification"
            "support_ticket"
        """
        prefix = template_prefix.split("/")[-1]
        logger.info("CustomAccountAdapter.send_mail → prefix=%s email=%s", prefix, email)

        # ------------------------------------------------------------------
        # IMPORTANT: strip allauth-provided subject so EmailEngine owns it
        # ------------------------------------------------------------------
        context.pop("subject", None)
        context.pop("email_subject", None)

        try:
            return self.email_engine.send(
                prefix,
                email,
                context,
                request=getattr(self, "request", None),
            )
        except Exception:
            logger.exception("CustomAccountAdapter.send_mail failed (prefix=%s)", prefix)
            raise



    # ------------------------------------------------------------------ #
    # Signup flow → delegate to service
    # ------------------------------------------------------------------ #
    def save_user(self, request, user, form, commit=True):
        """
        Thin wrapper. All heavy signup logic is handled by SignupFlowService.
        """
        result = SignupFlowService.handle_allauth_signup(request, user, form, commit)
        return result.user

    # ------------------------------------------------------------------ #
    # Email verification → delegate
    # ------------------------------------------------------------------ #
    def confirm_email(self, request, email_address):
        """
        Delegate domain rules to SignupFlowService.
        Maintain redstar bypass as existing behavior.
        """
        if email_address.email == "redstar@djangoplay.org":
            email_address.verified = True
            email_address.primary = True
            email_address.save()
            logger.info("Bypassed email confirmation for redstar@djangoplay.org")
            return

        SignupFlowService.handle_email_confirmation(email_address)
        return super().confirm_email(request, email_address)

    # ------------------------------------------------------------------ #
    # Login validation (unified)
    # ------------------------------------------------------------------ #
    def pre_login(self, request, user, **kwargs):
        """
        Enforce unified login validation rules BEFORE Allauth logs the user in.
        This ensures consistent rejection logic across all entrypoints.
        """
        # Allow 'redstar' to bypass all unified validation restrictions
        if user.username == "redstar":
            return

        validation = UnifiedLoginService.validate_user(user)
        if not validation.ok:
            if validation.reason == "EMAIL_NOT_VERIFIED":
                response = handle_unverified_email(
                    request=request,
                    email=user.email,
                    context="login",
                )
                raise ImmediateHttpResponse(response)

            messages.error(request, UnifiedLoginService.map_reason_to_message(validation.reason))
            raise ImmediateHttpResponse(HttpResponseRedirect(reverse("account_login")))


    # ------------------------------------------------------------------ #
    # Final login (unchanged)
    # ------------------------------------------------------------------ #
    def login(self, request, user):
        """
        Kept thin. All validation already happened in pre_login().
        """
        return super().login(request, user)

    # ------------------------------------------------------------------ #
    # Redirect handling (safer `next` support)
    # ------------------------------------------------------------------ #

    def get_login_redirect_url(self, request):
        """
        Minimal, non-opinionated adapter fallback.

        - If an explicit safe `next` param exists, return it.
        - Otherwise go to console dashboard.
        - Intercept redirect resolution before Allauth uses `next`.
        """
        current_host = request.get_host()

        # Respect safe next first
        redirect_to = get_request_param(request, "next")
        if redirect_to and redirect_to.startswith("/"):
            return redirect_to

        # Host-based redirect
        if current_host.startswith("issues."):
            return "/issues/"

        return reverse("console_dashboard")

    def get_logout_redirect_url(self, request):
        """
        Host-aware logout redirect.
        """
        current_host = request.get_host()
        if current_host.startswith("issues."):
            return "/issues/"

        return reverse("account_login")


    def is_safe_url(self, url, allowed_hosts=None):
        """
        Adds request host into allowed hosts automatically.
        Mirrors your previous behavior.
        """
        from django.utils.http import url_has_allowed_host_and_scheme

        allowed = set(allowed_hosts or []) | set(settings.ALLOWED_HOSTS or [])
        try:
            allowed.add(self.request.get_host())
        except Exception:
            pass

        return url_has_allowed_host_and_scheme(url, allowed_hosts=allowed)
