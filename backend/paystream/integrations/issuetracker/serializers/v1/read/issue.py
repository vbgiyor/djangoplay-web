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
from rest_framework import serializers


class IntegratedIssueReadSerializer(BaseIssueReadSerializer):
    attachments = IntegratedAttachmentReadSerializer(
        many=True,
        read_only=True,
    )

    # Comes from queryset annotation
    source = serializers.CharField(read_only=True)

    class Meta(BaseIssueReadSerializer.Meta):
        fields = BaseIssueReadSerializer.Meta.fields + ["source"]
