from django.urls import path

from .billing_schedule import BillingScheduleListAPIView
from .gst_configuration import GSTConfigurationListAPIView
from .invoice import InvoiceListAPIView
from .line_item import LineItemListAPIView
from .payment import PaymentListAPIView
from .payment_method import PaymentMethodListAPIView
from .status import StatusListAPIView

urlpatterns = [
    path("invoices/", InvoiceListAPIView.as_view()),
    path("line-items/", LineItemListAPIView.as_view()),
    path("payments/", PaymentListAPIView.as_view()),
    path("payment-methods/", PaymentMethodListAPIView.as_view()),
    path("statuses/", StatusListAPIView.as_view()),
    path("billing-schedules/", BillingScheduleListAPIView.as_view()),
    path("gst-configurations/", GSTConfigurationListAPIView.as_view()),
]
