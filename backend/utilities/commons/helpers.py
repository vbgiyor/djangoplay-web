import logging
from typing import Optional, Tuple

from django.conf import settings
from django.contrib.sites.models import Site
from users.services.identity_query_service import IdentityQueryService

logger = logging.getLogger(__name__)


def get_site_name() -> str:
    try:
        # First, try to get SITE_NAME from settings
        site_name = getattr(settings, "SITE_NAME", None)

        # If SITE_NAME is not set in settings, fall back to Site object
        if not site_name:
            site_name = Site.objects.get_current().name

    except Exception:
        # In case of any error, return the default site name
        site_name = getattr(settings, "SITE_NAME", "DjangoPlay")

    return site_name

def employee_state_by_email(email: str):
    """
    Identity-only resolution by email.

    Returns: (state, identity_or_employee_or_none)

    state ∈ {"ok", "not_found", "inactive", "unverified", "error"}
    """
    if not email:
        return "not_found", None

    email = email.strip().lower()

    try:
        identity = IdentityQueryService.get_by_email(email)

        if not identity:
            return "not_found", None

        # --------------------------------------------------
        # Support BOTH identity snapshot dicts AND models
        # --------------------------------------------------
        if isinstance(identity, dict):
            is_active = identity.get("is_active", True)
            is_verified = identity.get("is_verified", False)
        else:
            # Employee model fallback (current implementation)
            is_active = getattr(identity, "is_active", True)
            is_verified = getattr(identity, "is_verified", False)

        if not is_active:
            return "inactive", identity

        if not is_verified:
            return "unverified", identity

        return "ok", identity

    except Exception:
        logger.exception("employee_state_by_email failed for %s", email)
        return "error", None


def is_same_authenticated_user(request, result):
    return (
        request.user.is_authenticated
        and result.user
        and request.user.email.lower() == result.user.email.lower()
    )
