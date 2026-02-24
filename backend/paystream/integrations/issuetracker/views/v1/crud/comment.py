"""
Integrated Comment ViewSet
==========================

- Emits issue_commented signal
- Enforces RBAC visibility governance
"""

from django.db import transaction
from genericissuetracker.services.identity import get_identity_resolver
from genericissuetracker.signals import issue_commented
from genericissuetracker.views.v1.crud.comment import CommentCRUDViewSet
from paystream.integrations.issuetracker.services.visibility import (
    IssueVisibilityService,
)


class IntegratedCommentCRUDViewSet(CommentCRUDViewSet):

    """
    DjangoPlay-integrated Comment ViewSet.
    """

    # ----------------------------------------------------------
    # Visibility Governance
    # ----------------------------------------------------------
    def get_queryset(self):
        queryset = super().get_queryset()

        identity = get_identity_resolver().resolve(self.request)
        visibility = IssueVisibilityService(identity)

        return visibility.filter_comment_queryset(queryset)

    # ----------------------------------------------------------
    # Signal Emission
    # ----------------------------------------------------------
    def perform_create(self, serializer):
        identity = get_identity_resolver().resolve(self.request)

        with transaction.atomic():
            comment = serializer.save()

            issue_commented.send(
                sender=self.__class__,
                issue=comment.issue,
                comment=comment,
                identity=identity,
            )
