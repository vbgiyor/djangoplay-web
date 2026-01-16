from django.urls import path

from .address import AddressDetailAPIView
from .contact import ContactDetailAPIView
from .tax_profile import TaxProfileDetailAPIView

urlpatterns = [
    path("addresses/<uuid:pk>/", AddressDetailAPIView.as_view(), name="address-detail"),
    path("contacts/<uuid:pk>/", ContactDetailAPIView.as_view(), name="contact-detail"),
    path("tax-profiles/<uuid:pk>/", TaxProfileDetailAPIView.as_view(), name="tax-profile-detail"),
]
