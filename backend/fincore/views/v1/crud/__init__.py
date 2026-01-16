from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .address import AddressCrudViewSet
from .contact import ContactCRUDViewSet
from .tax_profile import TaxProfileCRUDViewSet

router = DefaultRouter()
router.register(r"addresses", AddressCrudViewSet, basename="address")
router.register(r"contacts", ContactCRUDViewSet, basename="contact")
router.register(r"tax-profiles", TaxProfileCRUDViewSet, basename="tax-profile")

urlpatterns = [
    path("", include(router.urls)),
]
