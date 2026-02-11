from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from teamcentral.models import LeaveType
from teamcentral.serializers.v1.read import LeaveTypeReadSerializerV1


@extend_schema(tags=["Teamcentral: Leave Type"])
class LeaveTypeHistoryAPIView(BaseHistoryListAPIView):
    queryset = LeaveType.objects.all()
    history_queryset = LeaveType.history.all()
    serializer_class = LeaveTypeReadSerializerV1
