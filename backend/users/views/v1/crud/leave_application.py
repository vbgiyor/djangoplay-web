from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from users.models import LeaveApplication
from users.serializers.v1.read import LeaveApplicationReadSerializerV1
from users.serializers.v1.write import LeaveApplicationWriteSerializerV1


@extend_schema(tags=["Users: Leave Application"])
class LeaveApplicationViewSet(BaseViewSet):
    queryset = LeaveApplication.objects.filter(deleted_at__isnull=True)

    read_serializer_class = LeaveApplicationReadSerializerV1
    write_serializer_class = LeaveApplicationWriteSerializerV1
