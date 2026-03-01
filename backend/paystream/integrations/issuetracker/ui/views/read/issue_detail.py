from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View
from django.http import Http404
from django.conf import settings

from genericissuetracker.models import Issue, IssueStatus
from genericissuetracker.services.identity import get_identity_resolver

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

            result = IssueMutationService.add_comment(
                issue=issue,
                request=request,
                body=request.POST.get("body"),
                commenter_email=request.POST.get("commenter_email"),
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
        identity = resolver.resolve(request)
        visibility = IssueVisibilityService(identity=identity)

        comment_queryset = visibility.filter_comment_queryset(
            issue.comments.all()
        )

        return {
            "issue": issue,
            "comments": comment_queryset,
            "allow_anonymous": getattr(
                settings,
                "GENERIC_ISSUETRACKER_ALLOW_ANONYMOUS_REPORTING",
                False,
            ),
            "status_choices": IssueStatus.choices,
            "identity": identity,
        }
