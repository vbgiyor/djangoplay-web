from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from invoices.models.invoice import Invoice
from invoices.serializers.v1.read import InvoiceListSerializer


@extend_schema(tags=["Invoices: Invoice"])
class InvoiceListAPIView(ListAPIView):

    """
    Read-only list of invoices.
    Safe for caching.
    """

    serializer_class = InvoiceListSerializer

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
            .order_by("-issue_date")
        )
