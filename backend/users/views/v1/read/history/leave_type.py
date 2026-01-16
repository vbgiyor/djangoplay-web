from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from users.models import LeaveType
from users.serializers.v1.read import LeaveTypeReadSerializerV1


@extend_schema(tags=["Users: Leave Type"])
class LeaveTypeHistoryAPIView(BaseHistoryListAPIView):
    queryset = LeaveType.objects.all()
    history_queryset = LeaveType.history.all()
    serializer_class = LeaveTypeReadSerializerV1
