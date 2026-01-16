from django.urls import path

from .address import AddressHistoryAPIView
from .contact import ContactHistoryAPIView
from .tax_profile import TaxProfileHistoryAPIView

urlpatterns = [
    path("addresses/<uuid:pk>/", AddressHistoryAPIView.as_view(), name="address-history"),
    path("contacts/<uuid:pk>/", ContactHistoryAPIView.as_view(), name="contact-history"),
    path("tax-profiles/<uuid:pk>/", TaxProfileHistoryAPIView.as_view(), name="tax-profile-history"),
]
