from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from users.models import FileUpload
from users.serializers.v1.read import FileUploadReadSerializerV1


@extend_schema(tags=["Users: File Upload"])
class FileUploadDetailAPIView(RetrieveAPIView):
    queryset = FileUpload.objects.filter(deleted_at__isnull=True)
    serializer_class = FileUploadReadSerializerV1
