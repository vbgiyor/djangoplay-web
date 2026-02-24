"""
Visibility Governance Service
=============================

Role-Based Visibility Governance (RBAC)

Design Principles
-----------------
- Explicit role-based access control
- Superuser override
- Queryset-level enforcement
- No serializer mutation
- No schema mutation
- No rank-based implicit privilege
- Deterministic behavior
"""

from django.conf import settings


class IssueVisibilityService:

    """
    Enforces RBAC visibility rules for IssueTracker.
    """

    def __init__(self, identity: dict):
        self.identity = identity

    # ----------------------------------------------------------
    # PRIVILEGE CHECK (RBAC)
    # ----------------------------------------------------------
    def _is_privileged(self) -> bool:

        if not self.identity.get("is_authenticated"):
            return False

        if self.identity.get("is_superuser"):
            return True

        allowed_roles = getattr(
            settings,
            "ISSUE_INTERNAL_ALLOWED_ROLES",
            [],
        )

        role_code = self.identity.get("role_code")

        return role_code in allowed_roles

    # ----------------------------------------------------------
    # QUERYSET FILTERING
    # ----------------------------------------------------------
    def filter_issue_queryset(self, queryset):
        if self._is_privileged():
            return queryset

        return queryset.filter(is_public=True)

    def filter_comment_queryset(self, queryset):
        if self._is_privileged():
            return queryset

        return queryset.filter(issue__is_public=True)

    def filter_attachment_queryset(self, queryset):
        if self._is_privileged():
            return queryset

        return queryset.filter(issue__is_public=True)
