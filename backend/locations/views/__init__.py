# locations/views/v1/__init__.py

from django.urls import include, path

app_name = "locations_v1"

urlpatterns = [
    path("crud/", include("locations.views.v1.crud")),
    path("read/", include("locations.views.v1.read")),
    path("ui/", include("locations.views.v1.ui")),
    path("ops/", include("locations.views.v1.ops")),
]
