from django.urls import path

from .billing_schedule import BillingScheduleHistoryAPIView
from .gst_configuration import GSTConfigurationHistoryAPIView
from .invoice import InvoiceHistoryAPIView
from .line_item import LineItemHistoryAPIView
from .payment import PaymentHistoryAPIView
from .payment_method import PaymentMethodHistoryAPIView
from .status import StatusHistoryAPIView

urlpatterns = [
    path("invoices/<int:pk>/", InvoiceHistoryAPIView.as_view()),
    path("line-items/<int:pk>/", LineItemHistoryAPIView.as_view()),
    path("payments/<int:pk>/", PaymentHistoryAPIView.as_view()),
    path("payment-methods/<int:pk>/", PaymentMethodHistoryAPIView.as_view()),
    path("statuses/<int:pk>/", StatusHistoryAPIView.as_view()),
    path("billing-schedules/<int:pk>/", BillingScheduleHistoryAPIView.as_view()),
    path("gst-configurations/<int:pk>/", GSTConfigurationHistoryAPIView.as_view()),
]
