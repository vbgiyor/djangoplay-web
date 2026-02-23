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
from users.models import Employee


class IssueVisibilityService:
    """
    Enforces RBAC visibility rules for IssueTracker.
    """

    def __init__(self, identity: dict):
        self.identity = identity
        self._employee = None

    # ----------------------------------------------------------
    # EMPLOYEE RESOLUTION
    # ----------------------------------------------------------
    def _get_employee(self):
        if not self.identity.get("is_authenticated"):
            return None

        if self._employee is not None:
            return self._employee

        user_id = self.identity.get("id")
        if not user_id:
            return None

        try:
            self._employee = Employee.objects.get(
                id=user_id,
                deleted_at__isnull=True,
            )
        except Employee.DoesNotExist:
            self._employee = None

        return self._employee

    # ----------------------------------------------------------
    # PRIVILEGE CHECK (RBAC)
    # ----------------------------------------------------------
    def _is_privileged(self) -> bool:
        employee = self._get_employee()
        if not employee:
            return False

        # Superuser override (industry standard)
        if employee.is_superuser:
            return True

        allowed_roles = getattr(
            settings,
            "ISSUE_INTERNAL_ALLOWED_ROLES",
            [],
        )

        role_code = getattr(employee.role, "code", None)

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