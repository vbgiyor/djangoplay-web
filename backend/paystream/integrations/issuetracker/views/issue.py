"""
Integrated Issue ViewSet
========================

- Emits issue_created signal
- Enforces RBAC visibility governance
"""

from django.db import transaction

from genericissuetracker.views.v1.crud.issue import IssueCRUDViewSet
from genericissuetracker.signals import issue_created
from genericissuetracker.services.identity import get_identity_resolver

from paystream.integrations.issuetracker.services.visibility import (
    IssueVisibilityService,
)


class IntegratedIssueCRUDViewSet(IssueCRUDViewSet):
    """
    DjangoPlay-integrated Issue ViewSet.
    """

    # ----------------------------------------------------------
    # Visibility Governance
    # ----------------------------------------------------------
    def get_queryset(self):
        queryset = super().get_queryset()

        identity = get_identity_resolver().resolve(self.request)
        visibility = IssueVisibilityService(identity)

        return visibility.filter_issue_queryset(queryset)

    # ----------------------------------------------------------
    # Signal Emission
    # ----------------------------------------------------------
    def perform_create(self, serializer):
        identity = get_identity_resolver().resolve(self.request)
        visibility = IssueVisibilityService(identity)

        with transaction.atomic():
            issue = serializer.save()
            
            # Enforce internal creation privilege
            if not visibility._is_privileged() and issue.is_public is False:
                issue.is_public = True
                issue.save(update_fields=["is_public"])

            issue_created.send(
                sender=self.__class__,
                issue=issue,
                identity=identity,
            )