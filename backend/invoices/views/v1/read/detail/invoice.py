from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from invoices.models.invoice import Invoice
from invoices.serializers.v1.read import InvoiceDetailSerializer


@extend_schema(tags=["Invoices: Invoice"])
class InvoiceDetailAPIView(RetrieveAPIView):
    serializer_class = InvoiceDetailSerializer

    def get_queryset(self):
        return (
            Invoice.objects
            .select_related(
                "issuer",
                "recipient",
                "billing_address",
                "billing_country",
                "billing_region",
                "status",
            )
            .filter(is_active=True)
        )
