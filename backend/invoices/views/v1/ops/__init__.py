from django.urls import path

from .bulk_status_update import InvoiceBulkStatusUpdateAPIView
from .invoice_export import InvoiceExportAPIView

urlpatterns = [
    path("export/invoices/", InvoiceExportAPIView.as_view()),
    path("bulk/invoices/status/", InvoiceBulkStatusUpdateAPIView.as_view()),
]
