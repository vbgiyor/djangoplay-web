from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from users.models import SupportTicket
from users.serializers.v1.read import SupportReadSerializerV1


@extend_schema(tags=["Users: Support"])
class SupportListAPIView(BaseListAPIView):
    queryset = SupportTicket.objects.filter(deleted_at__isnull=True)
    serializer_class = SupportReadSerializerV1
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "severity", "is_bug_report"]
