from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .billing_schedule import BillingScheduleViewSet
from .gst_configuration import GSTConfigurationViewSet
from .invoice import InvoiceViewSet
from .line_item import LineItemViewSet
from .payment import PaymentViewSet
from .payment_method import PaymentMethodViewSet
from .status import StatusViewSet

app_name = "invoices_v1_crud"

router = DefaultRouter()
router.register(r"invoices", InvoiceViewSet, basename="invoice")
router.register(r"line-items", LineItemViewSet, basename="line-item")
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(r"payment-methods", PaymentMethodViewSet, basename="payment-method")
router.register(r"statuses", StatusViewSet, basename="status")
router.register(r"gst-configurations", GSTConfigurationViewSet, basename="gst-configuration")
router.register(r"billing-schedules", BillingScheduleViewSet, basename="billing-schedule")

urlpatterns = [
    path("", include(router.urls)),
]
