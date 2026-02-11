from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from teamcentral.models import LeaveApplication
from teamcentral.serializers.v1.read import LeaveApplicationReadSerializerV1


@extend_schema(tags=["Teamcentral: Leave Application"])
class LeaveApplicationDetailAPIView(RetrieveAPIView):
    queryset = LeaveApplication.objects.filter(deleted_at__isnull=True)
    serializer_class = LeaveApplicationReadSerializerV1
