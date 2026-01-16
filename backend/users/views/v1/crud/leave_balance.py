from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from users.models import LeaveBalance
from users.serializers.v1.read import LeaveBalanceReadSerializerV1
from users.serializers.v1.write import LeaveBalanceWriteSerializerV1


@extend_schema(tags=["Users: Leave Balance"])
class LeaveBalanceViewSet(BaseViewSet):
    queryset = LeaveBalance.objects.filter(deleted_at__isnull=True)

    read_serializer_class = LeaveBalanceReadSerializerV1
    write_serializer_class = LeaveBalanceWriteSerializerV1
