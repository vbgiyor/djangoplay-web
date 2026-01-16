from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from invoices.models.payment import Payment
from invoices.serializers.v1.read import PaymentReadSerializer


@extend_schema(tags=["Invoices: Payment"])
class PaymentListAPIView(ListAPIView):
    serializer_class = PaymentReadSerializer

    def get_queryset(self):
        return (
            Payment.objects
            .select_related("invoice", "payment_method")
            .filter(is_active=True)
            .order_by("-payment_date")
        )
