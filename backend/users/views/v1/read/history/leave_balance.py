from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from users.models import LeaveBalance
from users.serializers.v1.read import LeaveBalanceReadSerializerV1


@extend_schema(tags=["Users: Leave Balance"])
class LeaveBalanceHistoryAPIView(BaseHistoryListAPIView):
    queryset = LeaveBalance.objects.all()
    history_queryset = LeaveBalance.history.all()
    serializer_class = LeaveBalanceReadSerializerV1
