from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from helpdesk.models import BugReport
from helpdesk.serializers.v1.read import BugReportReadSerializerV1


@extend_schema(tags=["Helpdesk: Bug"])
class BugReportListAPIView(BaseListAPIView):
    queryset = BugReport.objects.filter(
        deleted_at__isnull=True,
    )
    serializer_class = BugReportReadSerializerV1
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "severity"]
