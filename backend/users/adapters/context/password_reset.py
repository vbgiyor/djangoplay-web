# users/adapters/context/password_reset.py

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

        # If already provided (service explicitly passed it), do nothing
        if context.get("reset_url"):
            return context

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

# import logging
# from django.contrib.auth.tokens import default_token_generator
# from django.utils.http import int_to_base36
# from utilities.admin.url_utils import get_site_base_url
# from django.conf import settings

# logger = logging.getLogger(__name__)


# class PasswordResetContextProvider:

#     @staticmethod
#     def inject_password_reset_context(*, user, context: dict) -> dict:
#         """
#         Inject password-reset-specific context expected by templates.

#         This is intentionally small and isolated to avoid leaking
#         password reset logic into adapters or services.
#         """
#         if context is None:
#             context = {}

#         # Do not override if already provided (safety)
#         if context.get("reset_url"):
#             return context

#         uidb36 = int_to_base36(user.pk)
#         token = default_token_generator.make_token(user)
#         base_url = get_site_base_url()

#         context["reset_url"] = (
#             f"{base_url}/accounts/password/reset/key/{uidb36}/{token}/"
#         )

#         context.update(
#                 {
#                     'site_name': getattr(settings, 'SITE_NAME', 'DjangoPlay'),
#                 }
#             )

#         return context
