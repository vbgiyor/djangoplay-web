from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from users.models import FileUpload
from users.serializers.v1.read import FileUploadReadSerializerV1


@extend_schema(tags=["Users: File Upload"])
class FileUploadListAPIView(BaseListAPIView):
    queryset = FileUpload.objects.filter(deleted_at__isnull=True)
    serializer_class = FileUploadReadSerializerV1
