from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from invoices.models.payment import Payment
from invoices.serializers.v1.read import PaymentReadSerializer


@extend_schema(tags=["Invoices: Payment"])
class PaymentDetailAPIView(RetrieveAPIView):
    serializer_class = PaymentReadSerializer

    def get_queryset(self):
        return Payment.objects.filter(is_active=True)
