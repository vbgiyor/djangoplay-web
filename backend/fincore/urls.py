# fincore/urls.py

from django.urls import include, path

urlpatterns = [
    # Canonical versioned API
    path("", include("fincore.views.v1")),
]
