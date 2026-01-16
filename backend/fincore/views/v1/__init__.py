# fincore/views/v1/__init__.py

from django.urls import include, path

app_name = "fincore_v1"

urlpatterns = [
    # ------------------------------------------------------------------
    # CRUD APIs (write-capable, version-sensitive)
    # ------------------------------------------------------------------
    path(
        "crud/",
        include("fincore.views.v1.crud"),
    ),

    # ------------------------------------------------------------------
    # Read-only APIs (safe, cacheable)
    # ------------------------------------------------------------------
    path(
        "read/",
        include("fincore.views.v1.read"),
    ),

    # ------------------------------------------------------------------
    # UI-specific endpoints (Select2, admin UX helpers)
    # ------------------------------------------------------------------
    path(
        "ui/",
        include("fincore.views.v1.ui"),
    ),
]
