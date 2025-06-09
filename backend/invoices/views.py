from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Invoice, InvoiceStatus
from .serializers import InvoiceReadSerializer, InvoiceWriteSerializer


class IsNotSoftDeleted(permissions.BasePermission):

    """Custom permission to exclude soft-deleted invoices."""

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return getattr(obj, 'deleted_at', None) is None


class InvoiceViewSet(viewsets.ModelViewSet):

    """
    ViewSet for handling invoices:
    - Listing/filtering
    - Creating/updating
    - Soft deletion
    - Custom actions: mark_paid, cancel.
    """

    permission_classes = [permissions.IsAuthenticated, IsNotSoftDeleted]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['invoice_number', 'client__name', 'notes']
    ordering_fields = ['issue_date', 'due_date', 'amount', 'status__name']
    ordering = ['-issue_date']

    def get_queryset(self):
        """Return invoices that are not soft-deleted, with optional filtering."""
        queryset = Invoice.objects.select_related('client', 'status', 'payment_method')

        status_code = self.request.query_params.get('status')
        client_id = self.request.query_params.get('client_id')

        if status_code:
            queryset = queryset.filter(status__code=status_code)

        if client_id:
            queryset = queryset.filter(client__id=client_id)

        return queryset

    def get_serializer_class(self):
        if self.request.method in ['POST', 'PUT', 'PATCH']:
            return InvoiceWriteSerializer
        return InvoiceReadSerializer

    def perform_create(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """Perform a soft delete instead of a hard delete."""
        invoice = self.get_object()
        invoice.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        """Prevent updates on paid or cancelled invoices."""
        invoice = self.get_object()
        if invoice.status and invoice.status.code in ['paid', 'cancelled']:
            return Response(
                {"detail": "Paid or cancelled invoices cannot be edited."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        """Set invoice status to 'paid'."""
        invoice = self.get_object()
        if invoice.status and invoice.status.code == 'paid':
            return Response({"detail": "Invoice is already marked as paid."})

        paid_status = InvoiceStatus.objects.filter(code='paid').first()
        if not paid_status:
            return Response({"detail": "Status 'paid' not found."}, status=status.HTTP_400_BAD_REQUEST)

        invoice.status = paid_status
        invoice.save(update_fields=["status"])
        return Response({"detail": "Invoice marked as paid."})

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Set invoice status to 'cancelled'."""
        invoice = self.get_object()
        if invoice.status and invoice.status.code == 'cancelled':
            return Response({"detail": "Invoice is already cancelled."})

        cancelled_status = InvoiceStatus.objects.filter(code='cancelled').first()
        if not cancelled_status:
            return Response({"detail": "Status 'cancelled' not found."}, status=status.HTTP_400_BAD_REQUEST)

        invoice.status = cancelled_status
        invoice.save(update_fields=["status"])
        return Response({"detail": "Invoice cancelled."})
