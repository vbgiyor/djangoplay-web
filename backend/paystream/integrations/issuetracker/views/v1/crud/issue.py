"""
Integrated Issue ViewSet
========================

- Emits issue_created signal
- Enforces RBAC visibility governance
"""

from django.db import transaction
from genericissuetracker.services.identity import get_identity_resolver
from genericissuetracker.signals import issue_created, issue_deleted, issue_updated
from genericissuetracker.views.v1.crud.issue import IssueCRUDViewSet
from paystream.integrations.issuetracker.serializers.v1.read.issue import (
    IntegratedIssueReadSerializer,
)
from paystream.integrations.issuetracker.services.visibility import (
    IssueVisibilityService,
)


class IntegratedIssueCRUDViewSet(IssueCRUDViewSet):

    """
    DjangoPlay-integrated Issue ViewSet.
    """

    read_serializer_class = IntegratedIssueReadSerializer

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

    def perform_destroy(self, instance):
        identity = get_identity_resolver().resolve(self.request)

        instance.soft_delete()

        issue_deleted.send(
            sender=self.__class__,
            issue=instance,
            identity=identity,
        )

    def perform_update(self, serializer):
        identity = get_identity_resolver().resolve(self.request)

        instance = serializer.instance

        old_data = {
            "title": instance.title,
            "description": instance.description,
            "priority": instance.priority,
            "is_public": instance.is_public,
        }

        issue = serializer.save()

        new_data = {
            "title": issue.title,
            "description": issue.description,
            "priority": issue.priority,
            "is_public": issue.is_public,
        }

        if old_data != new_data:

            issue_updated.send(
                sender=self.__class__,
                issue=issue,
                old_data=old_data,
                new_data=new_data,
                identity=identity,
            )
