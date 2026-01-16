from django.urls import path

from .autocomplete import (
    InvoiceAutocompleteAPIView,
    PaymentMethodAutocompleteAPIView,
    StatusAutocompleteAPIView,
)

urlpatterns = [
    path("invoices/", InvoiceAutocompleteAPIView.as_view()),
    path("payment-methods/", PaymentMethodAutocompleteAPIView.as_view()),
    path("statuses/", StatusAutocompleteAPIView.as_view()),
]
