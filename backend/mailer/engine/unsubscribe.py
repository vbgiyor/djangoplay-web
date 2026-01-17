# mailer/engine/unsubscribe.py
import logging
from typing import Any, Optional, Tuple

from allauth.account.models import EmailAddress
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.db import transaction
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from utilities.admin.url_utils import get_site_base_url
from utilities.constants.unsubscribe import CATEGORY_BY_PREFIX, SYSTEM_EMAIL_PREFIXES

logger = logging.getLogger(__name__)

UNSUBSCRIBE_TOKEN_CACHE_TTL = 60 * 60 * 24  # 24 hours


class UnsubscribeService:

    """
    Unified unsubscribe infrastructure service.

    Owns:
    - unsubscribe eligibility checks
    - unsubscribe URL generation
    - unsubscribe token validation
    - resubscribe logic

    Does NOT own business policy decisions.
    """

    # ------------------------------------------------------
    # Eligibility check
    # ------------------------------------------------------
    @staticmethod
    def is_allowed(user, prefix: str) -> bool:
        if prefix in SYSTEM_EMAIL_PREFIXES:
            return True

        if not user:
            return True

        if getattr(user, "is_unsubscribed", False):
            logger.info("unsubscribe blocked (global) user=%s", user.email)
            return False

        prefs = getattr(user, "preferences", None)
        if isinstance(prefs, dict):
            category = CATEGORY_BY_PREFIX.get(prefix)
            if category and prefs.get(category) is False:
                logger.info(
                    "unsubscribe blocked (category=%s) user=%s",
                    category,
                    user.email,
                )
                return False

        return True

    # ------------------------------------------------------
    # URL generation
    # ------------------------------------------------------
    @staticmethod
    def build_unsubscribe_url(user) -> str:
        try:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            cache.set(
                f"unsubscribe:last_token:{user.pk}",
                token,
                UNSUBSCRIBE_TOKEN_CACHE_TTL,
            )

            path = reverse(
                "frontend:unsubscribe",
                kwargs={"uidb64": uid, "token": token},
            )
            return f"{get_site_base_url()}{path}"

        except Exception as exc:
            logger.exception("unsubscribe url build failed: %s", exc)
            return ""

    # ------------------------------------------------------
    # Token validation
    # ------------------------------------------------------
    @staticmethod
    def validate_unsubscribe_token(
        uidb64: str,
        token: str,
    ) -> Tuple[Optional[Any], Optional[str]]:
        if not uidb64 or not token:
            return None, "Missing unsubscribe link data."

        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = EmailAddress.objects.select_related("user").get(
                user__pk=uid,
                primary=True,
            ).user
        except Exception:
            return None, "Invalid unsubscribe link."

        if not user.is_active:
            return None, "This account is inactive."

        last_token = cache.get(f"unsubscribe:last_token:{user.pk}")
        if last_token and last_token != token:
            return None, "Invalid or expired unsubscribe link."

        if not default_token_generator.check_token(user, token):
            return None, "Invalid or expired unsubscribe link."

        return user, None

    # ------------------------------------------------------
    # Resubscribe
    # ------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def resubscribe_user(user) -> None:
        if not user:
            return

        user.is_unsubscribed = False
        user.unsubscribed_at = None
        user.save(update_fields=["is_unsubscribed", "unsubscribed_at"])

        EmailAddress.objects.filter(
            user=user,
            email__iexact=user.email,
        ).update(
            verified=True,
            primary=True,
        )
