from django.urls import path

from .autocomplete import (
    AddressAutocompleteView,
    ContactAutocompleteView,
    TaxProfileAutocompleteView,
)

urlpatterns = [
    path("autocomplete/addresses/", AddressAutocompleteView.as_view(), name="address-autocomplete"),
    path("autocomplete/contacts/", ContactAutocompleteView.as_view(), name="contact-autocomplete"),
    path("autocomplete/tax-profiles/", TaxProfileAutocompleteView.as_view(), name="tax-profile-autocomplete"),
]
