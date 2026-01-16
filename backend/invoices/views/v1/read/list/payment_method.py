from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from invoices.models.payment_method import PaymentMethod
from invoices.serializers.v1.read import PaymentMethodReadSerializer


@extend_schema(tags=["Invoices: Payment Method"])
class PaymentMethodListAPIView(ListAPIView):

    """
    Read-only list of payment methods.
    """

    serializer_class = PaymentMethodReadSerializer

    def get_queryset(self):
        return (
            PaymentMethod.objects
            .filter(is_active=True)
            .order_by("code")
        )
