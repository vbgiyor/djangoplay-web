"""
Integrated Issue Read Serializer
=================================

Overrides nested attachment serializer
to enforce secure download URLs.
"""

from genericissuetracker.serializers.v1.read.issue import (
    IssueReadSerializer as BaseIssueReadSerializer,
)
from paystream.integrations.issuetracker.serializers.v1.read.attachment import (
    IntegratedAttachmentReadSerializer,
)


class IntegratedIssueReadSerializer(BaseIssueReadSerializer):
    attachments = IntegratedAttachmentReadSerializer(
        many=True,
        read_only=True,
    )
