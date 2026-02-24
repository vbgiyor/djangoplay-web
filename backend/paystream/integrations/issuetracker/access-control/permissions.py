"""
IssueTracker Access Control
===========================

Contains:

1. IssueStateTransitionOwnerPolicy
   → Controls status transitions (change-status endpoint)

2. IssueTrackerAccessPermission
   → Enterprise DRF permission for IssueTracker endpoints
"""

from django.conf import settings
from rest_framework.permissions import SAFE_METHODS, BasePermission
from users.services.identity_login_policy_service import UnifiedLoginService
from users.services.identity_query_service import IdentityQueryService

# =====================================================================
# 1️⃣ Status Transition Policy
# =====================================================================

class IssueStateTransitionOwnerPolicy:

    """
    Allows status transition only for configured roles.

    Roles are defined in settings:

        ISSUE_STATUS_ALLOWED_ROLES = ["CEO", "DJGO", "SSO"]

    Used by GenericIssueTracker lifecycle transition system.
    """

    def can_transition(self, issue, old_status, new_status, identity):

        if not identity or not identity.get("is_authenticated"):
            return False

        user_id = identity.get("id")
        if not user_id:
            return False

        # Superuser bypass handled by login validation
        try:
            snapshot = IdentityQueryService.get_identity_snapshot(user_id)
        except Exception:
            return False

        if not snapshot["is_active"]:
            return False

        # Role restriction (if configured)
        allowed_roles = getattr(
            settings,
            "ISSUE_STATUS_ALLOWED_ROLES",
            [],
        )

        # Role must be passed via identity resolver (recommended extension)
        role_code = identity.get("role_code")

        if not allowed_roles:
            return True

        return role_code in allowed_roles


# =====================================================================
# 2️⃣ Enterprise DRF Permission
# =====================================================================

class IssueTrackerAccessPermission(BasePermission):

    """
    Enterprise-grade IssueTracker permission.

    Enforces:
    - UnifiedLoginService validation
    - Active employee requirement
    - EmploymentStatus == ACTV
    - Soft-delete guard
    - Optional role-based write restriction
    - Superuser override
    """

    message = "You do not have permission to access IssueTracker."

    # ----------------------------------------------------------
    # Unified Login Validation
    # ----------------------------------------------------------
    def _validate_user(self, user):

        if user.is_superuser:
            return True

        result = UnifiedLoginService.validate_user(user)

        return result.ok

    # ----------------------------------------------------------
    # Optional Write Role Restriction
    # ----------------------------------------------------------
    def _validate_write_role(self, identity):

        allowed_roles = getattr(
            settings,
            "ISSUE_WRITE_ALLOWED_ROLES",
            None,
        )

        if not allowed_roles:
            return True

        role_code = identity.get("role_code")

        return role_code in allowed_roles

    # ----------------------------------------------------------
    # Main Entry
    # ----------------------------------------------------------
    def has_permission(self, request, view):

        allow_anonymous = getattr(
            settings,
            "GENERIC_ISSUETRACKER_ALLOW_ANONYMOUS_REPORTING",
            False,
        )

        user = request.user

        # ------------------------------------------------------
        # READ endpoints
        # ------------------------------------------------------
        if request.method in SAFE_METHODS:
            return True

        # ------------------------------------------------------
        # WRITE endpoints
        # ------------------------------------------------------

        # Anonymous write (create only)
        if not user or not user.is_authenticated:
            if allow_anonymous and request.method == "POST":
                return True
            return False

        # Validate login rules
        if not self._validate_user(user):
            return False

        # Resolve identity snapshot (read-only)
        try:
            snapshot = IdentityQueryService.get_identity_snapshot(user.id)
        except Exception:
            return False

        if not snapshot["is_active"] or not snapshot["is_verified"]:
            return False

        # Validate role restriction
        identity = {
            "id": snapshot["id"],
            "email": snapshot["email"],
            "role_code": getattr(user, "role_code", None),
        }

        if not self._validate_write_role(identity):
            return False

        return True
