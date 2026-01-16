from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import ModelViewSet

from invoices.models.line_item import LineItem
from invoices.serializers.v1.read import LineItemReadSerializer
from invoices.serializers.v1.write import LineItemWriteSerializer


@extend_schema(tags=["Invoices: Line Item"])
class LineItemViewSet(ModelViewSet):
    queryset = (
        LineItem.objects
        .select_related("invoice")
        .filter(is_active=True)
        .order_by("id")
    )

    read_serializer_class = LineItemReadSerializer
    write_serializer_class = LineItemWriteSerializer

    def get_serializer_class(self):
        return (
            self.write_serializer_class
            if self.action in ("create", "update", "partial_update")
            else self.read_serializer_class
        )
