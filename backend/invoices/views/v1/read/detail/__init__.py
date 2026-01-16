from django.urls import path

from .billing_schedule import BillingScheduleDetailAPIView
from .gst_configuration import GSTConfigurationDetailAPIView
from .invoice import InvoiceDetailAPIView
from .line_item import LineItemDetailAPIView
from .payment import PaymentDetailAPIView
from .payment_method import PaymentMethodDetailAPIView
from .status import StatusDetailAPIView

urlpatterns = [
    path("invoices/<int:pk>/", InvoiceDetailAPIView.as_view()),
    path("line-items/<int:pk>/", LineItemDetailAPIView.as_view()),
    path("payments/<int:pk>/", PaymentDetailAPIView.as_view()),
    path("payment-methods/<int:pk>/", PaymentMethodDetailAPIView.as_view()),
    path("statuses/<int:pk>/", StatusDetailAPIView.as_view()),
    path("billing-schedules/<int:pk>/", BillingScheduleDetailAPIView.as_view()),
    path("gst-configurations/<int:pk>/", GSTConfigurationDetailAPIView.as_view()),
]
