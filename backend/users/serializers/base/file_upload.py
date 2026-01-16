from rest_framework import serializers

from users.models.file_upload import FileUpload


class BaseFileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileUpload
        fields = (
            "id",
            "file",
            "is_active",
        )
        read_only_fields = ("id",)
