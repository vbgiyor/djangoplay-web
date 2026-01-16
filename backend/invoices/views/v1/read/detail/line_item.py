from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from invoices.models.line_item import LineItem
from invoices.serializers.v1.read import LineItemReadSerializer


@extend_schema(tags=["Invoices: Line Item"])
class LineItemDetailAPIView(RetrieveAPIView):
    serializer_class = LineItemReadSerializer

    def get_queryset(self):
        return LineItem.objects.filter(is_active=True)
