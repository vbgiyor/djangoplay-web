from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from helpdesk.models import SupportTicket
from helpdesk.serializers.v1.read import SupportReadSerializerV1


@extend_schema(tags=["Helpdesk: Support"])
class SupportHistoryAPIView(BaseHistoryListAPIView):
    queryset = SupportTicket.objects.all()
    history_queryset = SupportTicket.history.all()
    serializer_class = SupportReadSerializerV1
