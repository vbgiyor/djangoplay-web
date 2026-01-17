import logging

from allauth.core.exceptions import ImmediateHttpResponse
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from mailer.engine.verification_guard import handle_unverified_email

from users.services.unified_login import UnifiedLoginService

logger = logging.getLogger(__name__)


class LoginValidationHelper:

    """
    ============================================================================
    UNIFIED LOGIN VALIDATION WRAPPER
    ----------------------------------------------------------------------------
    This provides a DRY wrapper for invoking UnifiedLoginService, raising
    ImmediateHttpResponse when validation fails.

    Used in:
        • CustomAccountAdapter.pre_login
        • CustomSocialAccountAdapter.authentication_successful
        • Any future login endpoints (mobile, API, CLI)
    ============================================================================
    """

    @staticmethod
    def enforce(request, user):
        """
        Validate and raise if login should not proceed.
        """
        # Redstar bypass always respected
        if getattr(user, "username", None) == "redstar":
            return

        validation = UnifiedLoginService.validate_user(user)
        if validation.ok:
            return

        if validation.reason == "EMAIL_NOT_VERIFIED":
            response = handle_unverified_email(
                request=request,
                email=user.email,
                context="login",
            )
            raise ImmediateHttpResponse(response)

        logger.error(
            "LoginValidationHelper: blocked login for %s: reason=%s",
            getattr(user, "email", None),
            validation.reason,
        )

        messages.error(request, UnifiedLoginService.map_reason_to_message(validation.reason))
        raise ImmediateHttpResponse(HttpResponseRedirect(reverse("account_login")))
