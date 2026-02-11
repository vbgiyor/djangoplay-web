from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from teamcentral.models import LeaveType
from teamcentral.serializers.v1.read import LeaveTypeReadSerializerV1


@extend_schema(tags=["Teamcentral: Leave Type"])
class LeaveTypeDetailAPIView(RetrieveAPIView):
    queryset = LeaveType.objects.filter(deleted_at__isnull=True)
    serializer_class = LeaveTypeReadSerializerV1
