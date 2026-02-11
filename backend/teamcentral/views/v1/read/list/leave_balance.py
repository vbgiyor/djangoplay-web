from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from teamcentral.models import LeaveBalance
from teamcentral.serializers.v1.read import LeaveBalanceReadSerializerV1


@extend_schema(tags=["Teamcentral: Leave Balance"])
class LeaveBalanceListAPIView(BaseListAPIView):
    queryset = LeaveBalance.objects.filter(deleted_at__isnull=True)
    serializer_class = LeaveBalanceReadSerializerV1
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["employee", "leave_type", "year"]
