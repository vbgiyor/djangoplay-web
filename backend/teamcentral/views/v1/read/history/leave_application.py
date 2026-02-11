from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from teamcentral.models import LeaveApplication
from teamcentral.serializers.v1.read import LeaveApplicationReadSerializerV1


@extend_schema(tags=["Teamcentral: Leave Application"])
class LeaveApplicationHistoryAPIView(BaseHistoryListAPIView):
    queryset = LeaveApplication.objects.all()
    history_queryset = LeaveApplication.history.all()
    serializer_class = LeaveApplicationReadSerializerV1
