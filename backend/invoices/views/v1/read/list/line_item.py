from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from invoices.models.line_item import LineItem
from invoices.serializers.v1.read import LineItemReadSerializer


@extend_schema(tags=["Invoices: Line Item"])
class LineItemListAPIView(ListAPIView):
    serializer_class = LineItemReadSerializer

    def get_queryset(self):
        return (
            LineItem.objects
            .select_related("invoice")
            .filter(is_active=True)
            .order_by("id")
        )
