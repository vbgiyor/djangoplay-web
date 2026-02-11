from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from teamcentral.models import LeaveBalance
from teamcentral.serializers.v1.read import LeaveBalanceReadSerializerV1


@extend_schema(tags=["Teamcentral: Leave Balance"])
class LeaveBalanceDetailAPIView(RetrieveAPIView):
    queryset = LeaveBalance.objects.filter(deleted_at__isnull=True)
    serializer_class = LeaveBalanceReadSerializerV1
