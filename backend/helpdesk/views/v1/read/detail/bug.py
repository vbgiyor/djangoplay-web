from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from helpdesk.models import BugReport
from helpdesk.serializers.v1.read import BugReportReadSerializerV1


@extend_schema(tags=["Helpdesk: Bug"])
class BugReportDetailAPIView(RetrieveAPIView):
    queryset = BugReport.objects.filter(
        deleted_at__isnull=True,
    )
    serializer_class = BugReportReadSerializerV1
