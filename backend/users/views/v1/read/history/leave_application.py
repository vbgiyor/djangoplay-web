from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from users.models import LeaveApplication
from users.serializers.v1.read import LeaveApplicationReadSerializerV1


@extend_schema(tags=["Users: Leave Application"])
class LeaveApplicationHistoryAPIView(BaseHistoryListAPIView):
    queryset = LeaveApplication.objects.all()
    history_queryset = LeaveApplication.history.all()
    serializer_class = LeaveApplicationReadSerializerV1
