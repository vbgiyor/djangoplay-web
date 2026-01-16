from django.urls import path

from .address import AddressListAPIView
from .contact import ContactListAPIView
from .tax_profile import TaxProfileListAPIView

urlpatterns = [
    path("addresses/", AddressListAPIView.as_view(), name="address-list"),
    path("contacts/", ContactListAPIView.as_view(), name="contact-list"),
    path("tax-profiles/", TaxProfileListAPIView.as_view(), name="tax-profile-list"),
]
