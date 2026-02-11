from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from helpdesk.models import BugReport
from helpdesk.serializers.v1.read import BugReportReadSerializerV1
from helpdesk.serializers.v1.write import BugReportWriteSerializerV1


@extend_schema(tags=["Helpdesk: Bug"])
class BugReportViewSet(BaseViewSet):
    queryset = BugReport.objects.filter(
        deleted_at__isnull=True,
    )

    read_serializer_class = BugReportReadSerializerV1
    write_serializer_class = BugReportWriteSerializerV1
