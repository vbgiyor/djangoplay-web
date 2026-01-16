from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from users.models import FileUpload
from users.serializers.v1.read import FileUploadReadSerializerV1
from users.serializers.v1.write import FileUploadWriteSerializerV1


@extend_schema(tags=["Users: File Upload"])
class FileUploadViewSet(BaseViewSet):
    queryset = FileUpload.objects.filter(deleted_at__isnull=True)

    read_serializer_class = FileUploadReadSerializerV1
    write_serializer_class = FileUploadWriteSerializerV1
