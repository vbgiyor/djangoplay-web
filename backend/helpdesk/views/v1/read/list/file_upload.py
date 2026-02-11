from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from helpdesk.models import FileUpload
from helpdesk.serializers.v1.read import FileUploadReadSerializerV1


@extend_schema(tags=["Helpdesk: File Upload"])
class FileUploadListAPIView(BaseListAPIView):
    queryset = FileUpload.objects.filter(deleted_at__isnull=True)
    serializer_class = FileUploadReadSerializerV1
