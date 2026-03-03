from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View
from genericissuetracker.models import IssuePriority
from genericissuetracker.settings import get_setting
from paystream.integrations.issuetracker.ui.services.issue_mutation_service import (
    IssueMutationService,
)


class IssueCreateView(View):

    """
    Issue creation view.

    Responsibilities:
        - Render creation form
        - Delegate creation to mutation service
        - Maintain PRG discipline
    """

    template_name = "issues/create.html"

    # ---------------------------------------------------------
    # GET
    # ---------------------------------------------------------
    def get(self, request):

        return render(
            request,
            self.template_name,
            {
                "priority_choices": IssuePriority.choices,
                "allow_anonymous": get_setting("ALLOW_ANONYMOUS_REPORTING"),
            },
        )

    # ---------------------------------------------------------
    # POST
    # ---------------------------------------------------------
    def post(self, request):

        result = IssueMutationService.create_issue(request=request)

        if result.success:
            messages.success(request, "Issue created successfully.")
            return redirect(
                "issues:detail",
                issue_number=result.issue.issue_number,
            )

        messages.error(request, result.error)

        return render(
            request,
            self.template_name,
            {
                "priority_choices": IssuePriority.choices,
                "allow_anonymous": get_setting("ALLOW_ANONYMOUS_REPORTING"),
            },
        )
