from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from invoices.exceptions import InvoiceValidationError
from invoices.models.invoice import Invoice
from invoices.models.status import Status


@extend_schema(exclude=True)
class InvoiceBulkStatusUpdateAPIView(APIView):

    """
    Bulk status update for invoices.

    Rules:
    - Admin-only
    - Explicit bulk intent
    - Never reused in CRUD
    """

    permission_classes = [IsAdminUser]

    def post(self, request):
        invoice_ids = request.data.get("invoice_ids", [])
        status_code = request.data.get("status")

        if not invoice_ids or not status_code:
            raise InvoiceValidationError(
                message="invoice_ids and status are required",
                code="invalid_bulk_payload",
            )

        try:
            status_obj = Status.objects.get(code=status_code, is_active=True)
        except Status.DoesNotExist:
            raise InvoiceValidationError(
                message="Invalid status code",
                code="invalid_status",
            )

        updated = (
            Invoice.objects
            .filter(id__in=invoice_ids, is_active=True)
            .update(status=status_obj)
        )

        return Response(
            {
                "updated_count": updated,
                "status": status_obj.code,
            },
            status=status.HTTP_200_OK,
        )
