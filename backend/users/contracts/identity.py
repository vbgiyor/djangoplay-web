"""
Public identity contract for external applications.

RULES:
- No Django model imports
- No ORM exposure
- No HR / organizational semantics
- Stable across versions

External apps MUST import from here.
"""

from typing import TypedDict


class IdentitySnapshot(TypedDict):

    """
    Serializable identity snapshot.
    """

    id: int
    email: str
    is_active: bool
    is_verified: bool


# ─────────────────────────────────────────────
# Read-only identity access
# ─────────────────────────────────────────────

def get_identity_snapshot(user_id: int) -> IdentitySnapshot:
    """
    Fetch stable identity data for a user.
    """
    from users.services.identity_query_service import IdentityQueryService

    return IdentityQueryService.get_identity_snapshot(user_id)


def is_user_verified(user_id: int) -> bool:
    """
    Lightweight verification check.
    """
    from users.services.identity_query_service import IdentityQueryService

    return IdentityQueryService.is_verified(user_id)


# ─────────────────────────────────────────────
# Delegated service access (EXISTING APIs ONLY)
# ─────────────────────────────────────────────

def validate_login_user(user):
    """
    Validate whether a user is allowed to log in.

    Thin wrapper over UnifiedLoginService.
    """
    from users.services.identity_login_policy_service import UnifiedLoginService

    return UnifiedLoginService.validate_user(user)


def send_password_reset_link(*, identifier: str, identifier_type: str, request):
    """
    Initiate password reset flow.

    Delegates to PasswordResetService.
    """
    from users.services.identity_password_reset_service import PasswordResetService

    return PasswordResetService.send_reset_link(
        identifier=identifier,
        identifier_type=identifier_type,
        request=request,
    )
