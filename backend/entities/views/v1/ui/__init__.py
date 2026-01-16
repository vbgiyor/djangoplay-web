from django.urls import path

from .autocomplete import EntityAutocompleteAPIView

urlpatterns = [
    path("autocomplete/entities/", EntityAutocompleteAPIView.as_view()),
]
