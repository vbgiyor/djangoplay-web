from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.views import View
from genericissuetracker.models import Issue, IssueStatus
from genericissuetracker.services.identity import get_identity_resolver
from genericissuetracker.settings import get_setting
from paystream.integrations.issuetracker.services.visibility import (
    IssueVisibilityService,
)
from paystream.integrations.issuetracker.ui.services.issue_mutation_service import (
    IssueMutationService,
)


class IssueDetailView(View):

    """
    Read-only Issue detail view.

    Responsibilities:
        - Resolve issue via service
        - Render template
        - Handle controlled write operations
    """

    template_name = "issues/detail.html"

    # ---------------------------------------------------------
    # GET
    # ---------------------------------------------------------
    def get(self, request, issue_number):

        issue = self._get_visible_issue(request, issue_number)

        context = self._build_context(request, issue)
        return render(request, self.template_name, context)

    # ---------------------------------------------------------
    # POST
    # ---------------------------------------------------------
    def post(self, request, issue_number):

        issue = self._get_visible_issue(request, issue_number)

        action = request.POST.get("action")

        if action == "add_comment":

            files = request.FILES.getlist("files")

            result = IssueMutationService.add_comment(
                issue=issue,
                request=request,
                body=request.POST.get("body"),
                commenter_email=request.POST.get("commenter_email"),
                files=files,
            )

            if result.success:
                messages.success(request, "Comment added.")
            else:
                messages.error(request, result.error)

        elif action == "change_status":

            result = IssueMutationService.change_status(
                issue=issue,
                request=request,
                new_status=request.POST.get("new_status"),
            )

            if result.success:
                messages.success(request, "Status updated.")
            else:
                messages.error(request, result.error)

        elif action == "add_attachment":

            result = IssueMutationService.add_attachments(
                issue=issue,
                request=request,
                files=request.FILES.getlist("files"),
            )

            if result.success:
                messages.success(request, "Files attached successfully.")
            else:
                messages.error(request, result.error)

        return redirect("issues:detail", issue_number=issue.issue_number)

    # ---------------------------------------------------------
    # Visibility-safe fetch
    # ---------------------------------------------------------
    def _get_visible_issue(self, request, issue_number):

        resolver = get_identity_resolver()
        identity = resolver.resolve(request) or {}
        visibility = IssueVisibilityService(identity=identity)

        queryset = visibility.filter_issue_queryset(
            Issue.objects.all()
        )

        try:
            return queryset.get(issue_number=issue_number)
        except Issue.DoesNotExist:
            raise Http404

    # ---------------------------------------------------------
    # Context
    # ---------------------------------------------------------
    def _build_context(self, request, issue):

        resolver = get_identity_resolver()
        identity = resolver.resolve(request) or {}
        visibility = IssueVisibilityService(identity=identity)

        comment_queryset = visibility.filter_comment_queryset(
            issue.comments.all()
        ).order_by("-created_at")

        attachment_queryset = visibility.filter_attachment_queryset(
            issue.attachments.all()
        )

        return {
            "issue": issue,
            "comments": comment_queryset,
            "attachments": attachment_queryset,
            "allow_anonymous": get_setting("ALLOW_ANONYMOUS_REPORTING"),
            "status_choices": IssueStatus.choices,
            "identity": identity,
            "can_change_status": identity.get("is_authenticated", False),
            "max_comment_length": get_setting("MAX_COMMENT_LENGTH"),
            "site_name": settings.SITE_NAME,
        }
