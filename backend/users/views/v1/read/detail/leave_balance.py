from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from users.models import LeaveBalance
from users.serializers.v1.read import LeaveBalanceReadSerializerV1


@extend_schema(tags=["Users: Leave Balance"])
class LeaveBalanceDetailAPIView(RetrieveAPIView):
    queryset = LeaveBalance.objects.filter(deleted_at__isnull=True)
    serializer_class = LeaveBalanceReadSerializerV1
