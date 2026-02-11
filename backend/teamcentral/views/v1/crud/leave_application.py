from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from teamcentral.models import LeaveApplication
from teamcentral.serializers.v1.read import LeaveApplicationReadSerializerV1
from teamcentral.serializers.v1.write import LeaveApplicationWriteSerializerV1


@extend_schema(tags=["Teamcentral: Leave Application"])
class LeaveApplicationViewSet(BaseViewSet):
    queryset = LeaveApplication.objects.filter(deleted_at__isnull=True)

    read_serializer_class = LeaveApplicationReadSerializerV1
    write_serializer_class = LeaveApplicationWriteSerializerV1
