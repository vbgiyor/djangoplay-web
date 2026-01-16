from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from invoices.models.line_item import LineItem
from invoices.serializers.v1.read import LineItemReadSerializer


@extend_schema(tags=["Invoices: Line Item"])
class LineItemHistoryAPIView(BaseHistoryListAPIView):
    serializer_class = LineItemReadSerializer

    def get_queryset(self):
        return (
            LineItem.history
            .filter(id=self.kwargs["pk"])
            .order_by("-history_date")
        )
