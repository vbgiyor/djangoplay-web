from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from invoices.models.status import Status
from invoices.serializers.v1.read import StatusReadSerializer


@extend_schema(tags=["Invoices: Status"])
class StatusHistoryAPIView(BaseHistoryListAPIView):
    serializer_class = StatusReadSerializer

    def get_queryset(self):
        return (
            Status.history
            .filter(id=self.kwargs["pk"])
            .order_by("-history_date")
        )
