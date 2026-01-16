from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from users.models import SupportTicket
from users.serializers.v1.read import SupportReadSerializerV1
from users.serializers.v1.write import SupportWriteSerializerV1


@extend_schema(tags=["Users: Support"])
class SupportViewSet(BaseViewSet):
    queryset = SupportTicket.objects.filter(deleted_at__isnull=True)

    read_serializer_class = SupportReadSerializerV1
    write_serializer_class = SupportWriteSerializerV1
