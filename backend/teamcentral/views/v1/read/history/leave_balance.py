from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from teamcentral.models import LeaveBalance
from teamcentral.serializers.v1.read import LeaveBalanceReadSerializerV1


@extend_schema(tags=["Teamcentral: Leave Balance"])
class LeaveBalanceHistoryAPIView(BaseHistoryListAPIView):
    queryset = LeaveBalance.objects.all()
    history_queryset = LeaveBalance.history.all()
    serializer_class = LeaveBalanceReadSerializerV1
