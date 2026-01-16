from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from users.models import LeaveBalance
from users.serializers.v1.read import LeaveBalanceReadSerializerV1


@extend_schema(tags=["Users: Leave Balance"])
class LeaveBalanceListAPIView(BaseListAPIView):
    queryset = LeaveBalance.objects.filter(deleted_at__isnull=True)
    serializer_class = LeaveBalanceReadSerializerV1
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["employee", "leave_type", "year"]
