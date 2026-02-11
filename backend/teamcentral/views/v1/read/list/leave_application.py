from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from teamcentral.models import LeaveApplication
from teamcentral.serializers.v1.read import LeaveApplicationReadSerializerV1


@extend_schema(tags=["Teamcentral: Leave Application"])
class LeaveApplicationListAPIView(BaseListAPIView):
    queryset = LeaveApplication.objects.filter(deleted_at__isnull=True)
    serializer_class = LeaveApplicationReadSerializerV1
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["employee", "status", "leave_type"]
