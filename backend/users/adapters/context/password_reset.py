import logging

from django.conf import settings
from django.utils import timezone
from utilities.admin.url_utils import get_site_base_url

from users.models.password_reset_request import PasswordResetRequest

logger = logging.getLogger(__name__)


class PasswordResetContextProvider:

    """
    Injects password reset context into email templates.

    Important:
    - Does NOT generate tokens
    - Does NOT invalidate tokens
    - Assumes token lifecycle is managed by the service layer

    """

    @staticmethod
    def inject_password_reset_context(*, user, context: dict) -> dict:
        if context is None:
            context = {}

        # FIX 3: Do NOT short-circuit on a pre-existing reset_url.
        # The service layer may pass a raw/encrypted token string as reset_url
        # instead of the correctly-formatted URL. Always rebuild from the DB
        # token to guarantee the URL is correct.
        #
        # REMOVED guard:
        #   if context.get("reset_url"):
        #       return context

        # Fetch latest ACTIVE reset request
        reset_req = (
            PasswordResetRequest.objects
            .filter(
                user=user,
                deleted_at__isnull=True,
                used=False,
                expires_at__gt=timezone.now(),
            )
            .order_by("-created_at")
            .first()
        )

        if not reset_req:
            logger.critical(
                "PasswordResetContextProvider: no active reset token found "
                "for user=%s",
                user.pk,
            )
            raise RuntimeError(
                "Password reset email requires an active PasswordResetRequest"
            )

        reset_url = (
            f"{get_site_base_url()}/accounts/password/reset/{reset_req.token}/"
        )

        context.update(
            {
                "reset_url": reset_url,
                "site_name": getattr(settings, "SITE_NAME", "DjangoPlay"),
            }
        )

        return context