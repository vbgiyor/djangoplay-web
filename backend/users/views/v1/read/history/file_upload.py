from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from users.models import FileUpload
from users.serializers.v1.read import FileUploadReadSerializerV1


@extend_schema(tags=["Users: File Upload"])
class FileUploadHistoryAPIView(BaseHistoryListAPIView):
    queryset = FileUpload.objects.all()
    history_queryset = FileUpload.history.all()
    serializer_class = FileUploadReadSerializerV1
