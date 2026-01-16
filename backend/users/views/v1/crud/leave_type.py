from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from users.models import LeaveType
from users.serializers.v1.read import LeaveTypeReadSerializerV1
from users.serializers.v1.write import LeaveTypeWriteSerializerV1


@extend_schema(tags=["Users: Leave Type"])
class LeaveTypeViewSet(BaseViewSet):
    queryset = LeaveType.objects.filter(deleted_at__isnull=True)

    read_serializer_class = LeaveTypeReadSerializerV1
    write_serializer_class = LeaveTypeWriteSerializerV1
