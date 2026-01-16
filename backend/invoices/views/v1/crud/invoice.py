from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import ModelViewSet

from invoices.models.invoice import Invoice
from invoices.serializers.v1.read import (
    InvoiceDetailSerializer,
    InvoiceListSerializer,
    InvoiceReadSerializer,
)
from invoices.serializers.v1.write import InvoiceWriteSerializer


@extend_schema(tags=["Invoices: Invoice"])
class InvoiceViewSet(ModelViewSet):

    """
    CRUD ViewSet for Invoice.
    """

    queryset = (
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

    read_serializer_class = InvoiceReadSerializer
    write_serializer_class = InvoiceWriteSerializer

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return self.write_serializer_class
        if self.action == "list":
            return InvoiceListSerializer
        if self.action == "retrieve":
            return InvoiceDetailSerializer
        return self.read_serializer_class
