import logging

from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse

from users.adapters.base import BaseAdapter
from users.models import Employee
from users.services.identity_login_policy_service import UnifiedLoginService
from users.services.identity_sso_onboarding_service import SSOOnboardingService

logger = logging.getLogger(__name__)


class CustomSocialAccountAdapter(BaseAdapter, DefaultSocialAccountAdapter):

    """
    ============================================================================
    CUSTOM SOCIAL ACCOUNT ADAPTER (THIN, SERVICE-ORIENTED)
    ----------------------------------------------------------------------------
    This adapter delegates all heavy SSO onboarding and account-matching logic
    to SSOOnboardingService so that this class remains a small Allauth glue
    layer only.

    It integrates:
      • Pre-social-login onboarding rules
      • Unified login validation
      • Email confirmation bypass for redstar
      • Clean error handling and redirect behavior

    No domain logic (employee creation, linking, verification, member setup)
    exists here — it is all handled in services.
    ============================================================================
    """

    # ------------------------------------------------------------------ #
    # Pre-social-login → delegate to SSOOnboardingService
    # ------------------------------------------------------------------ #
    def pre_social_login(self, request, sociallogin):
        """
        Delegate ALL SSO pre-processing to domain service.
        Adapter only handles:
            - capturing ImmediateHttpResponse from service
            - user-friendly error fallback
        """
        try:
            result = SSOOnboardingService.handle_pre_social_login(request, sociallogin)

            # If service requests early exit (redirect), return it
            if result.response is not None:
                raise ImmediateHttpResponse(result.response)

        except ImmediateHttpResponse:
            # bubble up final redirect (standard allauth behavior)
            raise

        except Exception as e:
            logger.exception("Unexpected error in pre_social_login: %s", e)
            messages.error(
                request,
                "An error occurred during social login. Please try again.",
            )
            raise ImmediateHttpResponse(HttpResponseRedirect(reverse("account_login")))

    # ------------------------------------------------------------------ #
    # Social signup → ensure Employee model consistency
    # ------------------------------------------------------------------ #
    def save_user(self, request, sociallogin, form=None):
        """
        Ensure correct model type. Heavy logic is done in SSOOnboardingService.
        """
        user = super().save_user(request, sociallogin, form)

        if not isinstance(user, Employee):
            logger.error("Expected Employee model after social signup, got %s", type(user))
            raise ValueError("Invalid user model for social login.")

        return user

    # ------------------------------------------------------------------ #
    # Login validation using unified login rules
    # ------------------------------------------------------------------ #
    def authentication_successful(self, request, sociallogin):
        """
        Called after allauth authenticates a user via SSO.

        Apply the same unified login rules as normal login flows.
        """
        user = sociallogin.user

        # Allow 'redstar' to bypass unified validation restrictions
        if user.username != "redstar":
            validation = UnifiedLoginService.validate_user(user)
            if not validation.ok:
                messages.error(request, UnifiedLoginService.map_reason_to_message(validation.reason))
                raise ImmediateHttpResponse(HttpResponseRedirect(reverse("account_login")))

        return super().authentication_successful(request, sociallogin)

    # ------------------------------------------------------------------ #
    # Disable default Allauth confirmation email for SSO
    # ------------------------------------------------------------------ #
    def send_confirmation_mail(self, request, emailconfirmation, signup):
        """
        SSO flows handle verification internally. Suppress Allauth emails.
        """
        logger.info(
            "CustomSocialAccountAdapter: Skipping default email confirmation for %s",
            emailconfirmation.email,
        )
        return

    # ------------------------------------------------------------------ #
    # Social-login cancel → standard friendly redirect
    # ------------------------------------------------------------------ #
    def social_login_cancelled(self, request):
        messages.info(request, "Login was cancelled. Please try again.")
        return HttpResponseRedirect(reverse("account_login"))
