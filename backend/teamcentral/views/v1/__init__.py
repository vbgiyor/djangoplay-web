from django.urls import include, path

app_name = "teamcentral_v1"

urlpatterns = [
    # ------------------------------------------------------------------
    # CRUD APIs (write-capable, versioned)
    # ------------------------------------------------------------------
    path(
        "crud/",
        include("teamcentral.views.v1.crud"),
    ),

    # ------------------------------------------------------------------
    # Read-only APIs (safe, cacheable, audit-friendly)
    # ------------------------------------------------------------------
    path(
        "read/",
        include("teamcentral.views.v1.read"),
    ),

    # ------------------------------------------------------------------
    # UI helpers (autocomplete, admin UX)
    # ------------------------------------------------------------------
    path(
        "ui/",
        include("teamcentral.views.v1.ui"),
    ),

    # ------------------------------------------------------------------
    # Operational / admin-only APIs
    # ------------------------------------------------------------------
    path(
        "ops/",
        include("teamcentral.views.v1.ops"),
    ),
]
