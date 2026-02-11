from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from helpdesk.models import BugReport
from helpdesk.serializers.v1.read import BugReportReadSerializerV1


@extend_schema(tags=["Helpdesk: Bug"])
class BugReportHistoryAPIView(BaseHistoryListAPIView):
    queryset = BugReport.objects.all()
    history_queryset = BugReport.history.all()
    serializer_class = BugReportReadSerializerV1
