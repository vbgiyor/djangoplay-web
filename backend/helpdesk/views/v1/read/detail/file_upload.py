from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from helpdesk.models import FileUpload
from helpdesk.serializers.v1.read import FileUploadReadSerializerV1


@extend_schema(tags=["Helpdesk: File Upload"])
class FileUploadDetailAPIView(RetrieveAPIView):
    queryset = FileUpload.objects.filter(deleted_at__isnull=True)
    serializer_class = FileUploadReadSerializerV1
