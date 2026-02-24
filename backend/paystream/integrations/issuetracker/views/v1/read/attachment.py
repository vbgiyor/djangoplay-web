"""
Integrated Attachment Read ViewSet
===================================

Uses secure serializer.
"""

from genericissuetracker.services.identity import get_identity_resolver
from genericissuetracker.views.v1.read.attachment import (
    AttachmentReadViewSet as BaseAttachmentReadViewSet,
)
from paystream.integrations.issuetracker.serializers.v1.read.attachment import (
    IntegratedAttachmentReadSerializer,
)
from paystream.integrations.issuetracker.services.visibility import (
    IssueVisibilityService,
)


class IntegratedAttachmentReadViewSet(BaseAttachmentReadViewSet):
    read_serializer_class = IntegratedAttachmentReadSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        identity = get_identity_resolver().resolve(self.request)
        visibility = IssueVisibilityService(identity)

        return visibility.filter_attachment_queryset(queryset)
