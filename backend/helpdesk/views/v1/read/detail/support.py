from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from helpdesk.models import SupportTicket
from helpdesk.serializers.v1.read import SupportReadSerializerV1


@extend_schema(tags=["Helpdesk: Support"])
class SupportDetailAPIView(RetrieveAPIView):
    queryset = SupportTicket.objects.filter(
        deleted_at__isnull=True,
    )
    serializer_class = SupportReadSerializerV1
