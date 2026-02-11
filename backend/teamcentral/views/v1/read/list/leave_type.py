from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from teamcentral.models import LeaveType
from teamcentral.serializers.v1.read import LeaveTypeReadSerializerV1


@extend_schema(tags=["Teamcentral: Leave Type"])
class LeaveTypeListAPIView(BaseListAPIView):
    queryset = LeaveType.objects.filter(deleted_at__isnull=True)
    serializer_class = LeaveTypeReadSerializerV1
