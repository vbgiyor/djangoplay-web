from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from invoices.models.payment import Payment
from invoices.serializers.v1.read import PaymentReadSerializer


@extend_schema(tags=["Invoices: Payment"])
class PaymentHistoryAPIView(BaseHistoryListAPIView):
    serializer_class = PaymentReadSerializer

    def get_queryset(self):
        return (
            Payment.history
            .filter(id=self.kwargs["pk"])
            .order_by("-history_date")
        )
