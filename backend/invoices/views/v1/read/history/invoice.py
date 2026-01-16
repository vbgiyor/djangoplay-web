from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from invoices.models.invoice import Invoice
from invoices.serializers.v1.read import InvoiceHistorySerializer


@extend_schema(tags=["Invoices: Invoice"])
class InvoiceHistoryAPIView(BaseHistoryListAPIView):

    """
    Historical changes for a single invoice (simple_history).
    """

    serializer_class = InvoiceHistorySerializer

    def get_queryset(self):
        return (
            Invoice.history
            .filter(id=self.kwargs["pk"])
            .order_by("-history_date")
        )
