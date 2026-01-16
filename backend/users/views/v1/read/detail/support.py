from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from users.models import SupportTicket
from users.serializers.v1.read import SupportReadSerializerV1


@extend_schema(tags=["Users: Support"])
class SupportDetailAPIView(RetrieveAPIView):
    queryset = SupportTicket.objects.filter(deleted_at__isnull=True)
    serializer_class = SupportReadSerializerV1
