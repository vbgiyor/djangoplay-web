from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from helpdesk.models import FileUpload
from helpdesk.serializers.v1.read import FileUploadReadSerializerV1
from helpdesk.serializers.v1.write import FileUploadWriteSerializerV1


@extend_schema(tags=["Helpdesk: File Upload"])
class FileUploadViewSet(BaseViewSet):
    queryset = FileUpload.objects.filter(deleted_at__isnull=True)

    read_serializer_class = FileUploadReadSerializerV1
    write_serializer_class = FileUploadWriteSerializerV1
