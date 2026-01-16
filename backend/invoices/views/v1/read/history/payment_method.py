from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from invoices.models.payment_method import PaymentMethod
from invoices.serializers.v1.read import PaymentMethodReadSerializer


@extend_schema(tags=["Invoices: Payment Method"])
class PaymentMethodHistoryAPIView(BaseHistoryListAPIView):
    serializer_class = PaymentMethodReadSerializer

    def get_queryset(self):
        return (
            PaymentMethod.history
            .filter(id=self.kwargs["pk"])
            .order_by("-history_date")
        )
