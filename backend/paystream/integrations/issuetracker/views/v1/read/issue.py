"""
Integrated Issue Read ViewSet
=============================

- Applies RBAC visibility
- Uses secure nested attachment serializer
"""

from genericissuetracker.services.identity import get_identity_resolver
from genericissuetracker.views.v1.read.issue import (
    IssueReadViewSet as BaseIssueReadViewSet,
)
from paystream.integrations.issuetracker.serializers.v1.read.issue import (
    IntegratedIssueReadSerializer,
)
from paystream.integrations.issuetracker.services.visibility import (
    IssueVisibilityService,
)


class IntegratedIssueReadViewSet(BaseIssueReadViewSet):
    read_serializer_class = IntegratedIssueReadSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        identity = get_identity_resolver().resolve(self.request)
        visibility = IssueVisibilityService(identity)

        return visibility.filter_issue_queryset(queryset)
