from helpdesk.serializers.base import BaseFileUploadSerializer


class FileUploadReadSerializerV1(BaseFileUploadSerializer):
    class Meta(BaseFileUploadSerializer.Meta):
        fields = BaseFileUploadSerializer.Meta.fields + (
            "uploaded_at",
        )
