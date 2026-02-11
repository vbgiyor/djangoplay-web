from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from helpdesk.models import FileUpload
from helpdesk.serializers.v1.read import FileUploadReadSerializerV1


@extend_schema(tags=["Helpdesk: File Upload"])
class FileUploadHistoryAPIView(BaseHistoryListAPIView):
    queryset = FileUpload.objects.all()
    history_queryset = FileUpload.history.all()
    serializer_class = FileUploadReadSerializerV1
