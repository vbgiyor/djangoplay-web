# users/views/v1/__init__.py

from django.urls import include, path

app_name = "users_v1"

urlpatterns = [
    # ------------------------------------------------------------------
    # Authentication & identity flows
    # ------------------------------------------------------------------
    path(
        "auth/",
        include("users.views.v1.auth"),
    ),

    # ------------------------------------------------------------------
    # CRUD APIs (write-capable, versioned)
    # ------------------------------------------------------------------
    path(
        "crud/",
        include("users.views.v1.crud"),
    ),

    # ------------------------------------------------------------------
    # Read-only APIs (safe, cacheable, audit-friendly)
    # ------------------------------------------------------------------
    path(
        "read/",
        include("users.views.v1.read"),
    ),

    # ------------------------------------------------------------------
    # UI helpers (autocomplete, admin UX)
    # ------------------------------------------------------------------
    path(
        "ui/",
        include("users.views.v1.ui"),
    ),

    # ------------------------------------------------------------------
    # Operational / admin-only APIs
    # ------------------------------------------------------------------
    path(
        "ops/",
        include("users.views.v1.ops"),
    ),
]
