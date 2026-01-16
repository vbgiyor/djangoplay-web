import logging
from typing import Any, Optional, Tuple

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.utils.http import urlsafe_base64_decode

logger = logging.getLogger(__name__)

User = get_user_model()


def validate_unsubscribe_token(uidb64: str, token: str) -> Tuple[Optional[Any], Optional[str]]:
    """
    Validates unsubscribe link and returns user if valid, error message if invalid.
    """
    if not uidb64 or not token:
        return None, "Missing unsubscribe link data."

    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None, "Invalid unsubscribe link."

    if not user.is_active:
        return None, "This account is inactive."

    email_obj = EmailAddress.objects.filter(
        user=user,
        email=user.email,
    ).first()

    if not email_obj:
        if getattr(user, "is_unsubscribed", False):
            return None, "You have already unsubscribed from emails for this address."
        return None, "This unsubscribe link is no longer valid."

    # --------------------------------------------------
    # 🔒 INVALIDATE OLDER UNSUBSCRIBE LINKS (CACHE-BASED)
    # --------------------------------------------------
    cache_key = f"unsubscribe:last_token:{user.pk}"
    last_token = cache.get(cache_key)

    if last_token and last_token != token:
        return None, "Invalid or expired unsubscribe link."

    if not email_obj.verified:
        return None, "You have already unsubscribed from emails for this address."

    if not default_token_generator.check_token(user, token):
        return None, "Invalid or expired unsubscribe link."

    return user, None
