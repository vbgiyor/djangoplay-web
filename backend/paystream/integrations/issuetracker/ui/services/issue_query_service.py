
from django.db.models import Count, QuerySet
from genericissuetracker.models import Issue, IssueStatus
from genericissuetracker.services.pagination import resolve_page_size
from paystream.integrations.issuetracker.services.visibility import (
    IssueVisibilityService,
)


class IssueQueryService:

    """
    Service responsible for constructing Issue list querysets
    for UI consumption.

    Responsibilities:
        - Base queryset construction
        - Visibility filtering
        - Enum-driven status filtering
        - Deterministic ordering

    No business logic.
    No permission logic duplication.
    """

    @staticmethod
    def get_issues_for_list(user, status: str | None = None) -> QuerySet:
        """
        Returns queryset of issues visible to the given user,
        optionally filtered by status.
        """
        # Base queryset (soft-delete automatically respected)
        queryset = Issue.objects.all().annotate(
                comment_count=Count("comments", distinct=True)
            )
        # Apply integration visibility governance
        identity = {
            "is_authenticated": user.is_authenticated,
            "is_superuser": getattr(user, "is_superuser", False),
            "role_code": getattr(user, "role_code", None),
        }

        visibility_service = IssueVisibilityService(identity=identity)

        queryset = visibility_service.filter_issue_queryset(queryset)

        # Enum-driven status filtering
        if status and status != "ALL":
            valid_statuses = {choice[0] for choice in IssueStatus.choices}
            if status in valid_statuses:
                queryset = queryset.filter(status=status)

        return queryset.order_by("-created_at")

    @staticmethod
    def get_page_size() -> int:
        """
        Resolve page size from genericissuetracker settings.
        """
        return resolve_page_size()
