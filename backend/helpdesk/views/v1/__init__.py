from django.urls import include, path

app_name = "helpdesk_v1"

urlpatterns = [
    # ------------------------------------------------------------------
    # CRUD APIs (write-capable, versioned)
    # ------------------------------------------------------------------
    path(
        "crud/",
        include("helpdesk.views.v1.crud"),
    ),

    # ------------------------------------------------------------------
    # Read-only APIs (safe, cacheable, audit-friendly)
    # ------------------------------------------------------------------
    path(
        "read/",
        include("helpdesk.views.v1.read"),
    ),

    # ------------------------------------------------------------------
    # UI helpers (autocomplete, admin UX)
    # ------------------------------------------------------------------
    path(
        "ui/",
        include("helpdesk.views.v1.ui"),
    ),
]
