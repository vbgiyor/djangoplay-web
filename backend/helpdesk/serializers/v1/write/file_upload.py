from helpdesk.serializers.base import BaseFileUploadSerializer


class FileUploadWriteSerializerV1(BaseFileUploadSerializer):
    class Meta(BaseFileUploadSerializer.Meta):
        fields = (
            "file",
            "is_active",
        )
