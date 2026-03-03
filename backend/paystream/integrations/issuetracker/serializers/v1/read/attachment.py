"""
Attachment Serializer Override
===============================

Removes public MEDIA exposure.
Provides secure download endpoint only.
"""

from django.urls import reverse
from drf_spectacular.utils import extend_schema_field
from genericissuetracker.serializers.v1.read.attachment import (
    IssueAttachmentReadSerializer,
)
from rest_framework import serializers


class IntegratedAttachmentReadSerializer(IssueAttachmentReadSerializer):

    """
    Secure attachment serializer.

    - Hides raw file path
    - Exposes secure download endpoint
    """

    download_url = serializers.SerializerMethodField()

    class Meta(IssueAttachmentReadSerializer.Meta):
        fields = [
            "id",
            "number",
            "issue",
            "comment",
            "original_name",
            "size",
            "uploaded_by_user_id",
            "uploaded_by_email",
            "created_at",
            "updated_at",
            "download_url",
        ]

    @extend_schema_field(serializers.URLField())
    def get_download_url(self, obj) -> str:
        request = self.context.get("request")

        url = reverse(
            "issuetracker-attachment-download",
            kwargs={"number": obj.number},
        )

        if request:
            return request.build_absolute_uri(url)

        return url
