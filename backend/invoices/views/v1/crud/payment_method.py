from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import ModelViewSet

from invoices.models.payment_method import PaymentMethod
from invoices.serializers.v1.read import PaymentMethodReadSerializer
from invoices.serializers.v1.write import PaymentMethodWriteSerializer


@extend_schema(tags=["Invoices: Payment Method"])
class PaymentMethodViewSet(ModelViewSet):
    queryset = PaymentMethod.objects.filter(is_active=True).order_by("code")

    read_serializer_class = PaymentMethodReadSerializer
    write_serializer_class = PaymentMethodWriteSerializer

    def get_serializer_class(self):
        return (
            self.write_serializer_class
            if self.action in ("create", "update", "partial_update")
            else self.read_serializer_class
        )
