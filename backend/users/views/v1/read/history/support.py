from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from users.models import SupportTicket
from users.serializers.v1.read import SupportReadSerializerV1


@extend_schema(tags=["Users: Support"])
class SupportHistoryAPIView(BaseHistoryListAPIView):
    queryset = SupportTicket.objects.all()
    history_queryset = SupportTicket.history.all()
    serializer_class = SupportReadSerializerV1
