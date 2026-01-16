# locations/views/v1/__init__.py

from django.urls import include, path

app_name = "locations_v1"

urlpatterns = [
    # ------------------------------------------------------------------
    # CRUD APIs (write-capable, version-sensitive)
    # ------------------------------------------------------------------
    path(
        "crud/",
        include("locations.views.v1.crud"),
    ),

    # ------------------------------------------------------------------
    # Read-only APIs (safe, cacheable)
    # ------------------------------------------------------------------
    path(
        "read/",
        include("locations.views.v1.read"),
    ),

    # ------------------------------------------------------------------
    # UI-specific endpoints (Select2, admin UX helpers)
    # ------------------------------------------------------------------
    path(
        "ui/",
        include("locations.views.v1.ui"),
    ),

    # ------------------------------------------------------------------
    # Operational / admin-only APIs (bulk, export)
    # ------------------------------------------------------------------
    path(
        "ops/",
        include("locations.views.v1.ops"),
    ),
]
