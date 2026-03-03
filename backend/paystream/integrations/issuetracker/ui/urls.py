from django.urls import path
from paystream.integrations.issuetracker.ui.views.crud.issue import IssueCreateView
from paystream.integrations.issuetracker.ui.views.read.issue_detail import IssueDetailView
from paystream.integrations.issuetracker.ui.views.read.issue_list import IssueListView
from paystream.integrations.issuetracker.ui.views.root import IssueRootRedirectView

app_name = "issues"

urlpatterns = [
    path("", IssueRootRedirectView.as_view(), name="root"),
    path("issues/", IssueListView.as_view(), name="list"),
    path("issues/new/", IssueCreateView.as_view(), name="create"),
    path("issues/<int:issue_number>/", IssueDetailView.as_view(), name="detail"),
]
