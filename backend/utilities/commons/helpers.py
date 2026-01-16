import logging
from typing import Optional, Tuple

from django.conf import settings
from django.contrib.sites.models import Site
from users.models import Employee, Member

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

def employee_state_by_email(email: str) -> Tuple[str, Optional[Employee]]:
    """
    Generic helper: resolve employee (direct or via Member) and return a state.

    Returns: (state, employee_or_none)
      state in {"ok", "not_found", "inactive", "unverified", "error"}.

    - "ok": employee exists and is active & verified (or no employee exists at all; caller
            may treat "not_found" differently if they want).
    - "not_found": no Employee (nor Member->Employee) for this email.
    - "inactive": employee exists but is soft-deleted / inactive.
    - "unverified": employee exists but is not verified.
    - "error": an exception occurred while resolving (defensive).
    """
    if not email:
        return "not_found", None

    email = email.strip().lower()
    try:
        # Prefer a non-filtering manager if present so soft-deleted records can be inspected.
        emp_manager = getattr(Employee, "all_objects", None) or getattr(Employee, "objects", None)
        emp = emp_manager.filter(email__iexact=email).first()

        # Members in your architecture are backed by Employees; try Member -> employee fallback.
        if not emp:
            mem_manager = getattr(Member, "all_objects", None) or getattr(Member, "objects", None)
            mem = mem_manager.filter(email__iexact=email).first()
            emp = getattr(mem, "employee", None) if mem else None

        if not emp:
            return "not_found", None

        # Detect soft-delete / inactive. Prefer model property if present.
        is_soft_deleted = getattr(emp, "is_soft_deleted", None)
        if is_soft_deleted is None:
            is_soft_deleted = bool(getattr(emp, "deleted_at", None)) or (getattr(emp, "is_active", True) is False)

        if is_soft_deleted:
            return "inactive", emp

        # Detect verified. Prefer model property if present.
        is_verified = getattr(emp, "is_verified_account", None)
        if is_verified is None:
            is_verified = bool(getattr(emp, "is_verified", False))

        if not is_verified:
            return "unverified", emp

        return "ok", emp

    except Exception:
        logger.exception("employee_state_by_email failed for %s", email)
        # Defensive: return 'error' so callers can decide to allow/deny
        return "error", None

def is_same_authenticated_user(request, result):
    return (
        request.user.is_authenticated
        and result.user
        and request.user.email.lower() == result.user.email.lower()
    )
