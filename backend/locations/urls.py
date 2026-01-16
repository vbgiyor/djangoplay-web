# locations/urls.py

from django.urls import include, path

urlpatterns = [
    # Canonical versioned API
    path("",include("locations.views.v1")),
]
