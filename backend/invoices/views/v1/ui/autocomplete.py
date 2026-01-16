from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from invoices.models.invoice import Invoice
from invoices.models.payment_method import PaymentMethod
from invoices.models.status import Status
from invoices.serializers.v1.read import (
    InvoiceListSerializer,
    PaymentMethodReadSerializer,
    StatusReadSerializer,
)


@extend_schema(exclude=True)
class InvoiceAutocompleteAPIView(ListAPIView):

    """
    Lightweight invoice autocomplete.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = InvoiceListSerializer

    def get_queryset(self):
        q = self.request.query_params.get("q", "")
        return (
            Invoice.objects
            .filter(
                is_active=True,
                invoice_number__icontains=q,
            )
            .order_by("-issue_date")[:20]
        )


@extend_schema(exclude=True)
class PaymentMethodAutocompleteAPIView(ListAPIView):

    """
    Payment method autocomplete.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PaymentMethodReadSerializer

    def get_queryset(self):
        q = self.request.query_params.get("q", "")
        return (
            PaymentMethod.objects
            .filter(is_active=True, name__icontains=q)
            .order_by("name")[:20]
        )


@extend_schema(exclude=True)
class StatusAutocompleteAPIView(ListAPIView):

    """
    Invoice status autocomplete.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = StatusReadSerializer

    def get_queryset(self):
        q = self.request.query_params.get("q", "")
        return (
            Status.objects
            .filter(is_active=True, name__icontains=q)
            .order_by("name")[:20]
        )
