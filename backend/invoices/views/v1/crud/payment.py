from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import ModelViewSet

from invoices.models.payment import Payment
from invoices.serializers.v1.read import PaymentReadSerializer
from invoices.serializers.v1.write import PaymentWriteSerializer


@extend_schema(tags=["Invoices: Payment"])
class PaymentViewSet(ModelViewSet):
    queryset = (
        Payment.objects
        .select_related("invoice", "payment_method")
        .filter(is_active=True)
        .order_by("-payment_date")
    )

    read_serializer_class = PaymentReadSerializer
    write_serializer_class = PaymentWriteSerializer

    def get_serializer_class(self):
        return (
            self.write_serializer_class
            if self.action in ("create", "update", "partial_update")
            else self.read_serializer_class
        )
