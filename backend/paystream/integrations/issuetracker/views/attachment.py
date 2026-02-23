"""
Integrated Attachment ViewSet
=============================

Enforces RBAC visibility governance.
"""

from genericissuetracker.views.v1.crud.attachment import (
    AttachmentCRUDViewSet,
)

from genericissuetracker.services.identity import get_identity_resolver

from paystream.integrations.issuetracker.services.visibility import (
    IssueVisibilityService,
)


class IntegratedAttachmentCRUDViewSet(AttachmentCRUDViewSet):
    """
    DjangoPlay-integrated Attachment ViewSet.
    """

    def get_queryset(self):
        queryset = super().get_queryset()

        identity = get_identity_resolver().resolve(self.request)
        visibility = IssueVisibilityService(identity)

        return visibility.filter_attachment_queryset(queryset)