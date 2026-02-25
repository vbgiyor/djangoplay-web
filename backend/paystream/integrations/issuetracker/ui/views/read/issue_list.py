from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.views import View
from genericissuetracker.models import IssueStatus
from paystream.integrations.issuetracker.ui.services.issue_query_service import (
    IssueQueryService,
)
from utilities.constants.template_registry import TemplateRegistry as T


class IssueListView(View):

    """
    Server-rendered Issue list view.

    Thin orchestration layer:
        - Host validation
        - Query param parsing
        - Service call
        - Pagination
        - Template rendering
    """

    template_name = T.ISSUES_LIST

    def get(self, request):
        status = request.GET.get("status", "ALL")

        queryset = IssueQueryService.get_issues_for_list(
            user=request.user,
            status=status,
        )

        page_size = IssueQueryService.get_page_size()

        paginator = Paginator(queryset, page_size)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context = {
            "page_obj": page_obj,
            "status_filter": status,
            "status_choices": IssueStatus.choices,
        }

        return render(request, self.template_name, context)
