from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from invoices.models.invoice import Invoice
from invoices.serializers.v1.read import InvoiceReadSerializer


@extend_schema(exclude=True)
class InvoiceExportAPIView(APIView):

    """
    Admin-only invoice export endpoint.

    Characteristics:
    - Read-only
    - Derived output
    - Explicit admin permission
    - No reuse in CRUD
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = (
            Invoice.objects
            .select_related(
                "issuer",
                "recipient",
                "billing_country",
                "billing_region",
                "status",
            )
            .filter(is_active=True)
            .order_by("-issue_date")
        )

        serializer = InvoiceReadSerializer(queryset, many=True)
        return Response(serializer.data)
