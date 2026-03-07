
from django.db.models import Case, CharField, Count, Exists, OuterRef, QuerySet, Value, When
from genericissuetracker.models import Issue, IssueStatus
from genericissuetracker.services.pagination import resolve_page_size
from helpdesk.models import BugReport
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
        queryset = (
            Issue.objects.all()
            .annotate(
                comment_count=Count("comments", distinct=True),

                is_bug=Exists(
                    BugReport.objects.filter(
                        migrated_issue_id=OuterRef("id")
                    )
                ),
            )
            .annotate(
                source=Case(
                    When(is_bug=True, then=Value("bug_report")),
                    default=Value("issue"),
                    output_field=CharField(),
                )
            )
        )

        identity = {
            "is_authenticated": user.is_authenticated,
            "is_superuser": getattr(user, "is_superuser", False),
            "role_code": getattr(getattr(user, "role", None), "code", None),
        }

        visibility_service = IssueVisibilityService(identity=identity)

        # # Anonymous users can see internal issues in LIST only
        if user.is_authenticated:
            queryset = visibility_service.filter_issue_queryset(queryset)

        if status and status != "ALL":
            valid_statuses = {choice[0] for choice in IssueStatus.choices}
            if status in valid_statuses:
                queryset = queryset.filter(status=status)

        return queryset.order_by("-created_at")


    @staticmethod
    def get_issue_for_detail(request, issue_number: int):

        from django.http import Http404
        queryset = (
            Issue.objects.all()
            .prefetch_related(
                "comments",
                "attachments",
                "status_history",
            )
        )
        try:
            return queryset.get(issue_number=issue_number)
        except Issue.DoesNotExist:
            raise Http404("Issue not found")


    @staticmethod
    def get_page_size() -> int:
        """
        Resolve page size from genericissuetracker settings.
        """
        return resolve_page_size()
