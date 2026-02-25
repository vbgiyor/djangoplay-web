from django.urls import path
from paystream.integrations.issuetracker.ui.views.read.issue_list import (
    IssueListView,
)
from paystream.integrations.issuetracker.ui.views.root import (
    IssueRootRedirectView,
)

app_name = "issues"

urlpatterns = [
    path("", IssueRootRedirectView.as_view(), name="root"),
    path("issues/", IssueListView.as_view(), name="list"),
]
