# invoices/views/v1/__init__.py

from django.urls import include, path

app_name = "invoices_v1"

urlpatterns = [
    # --------------------------------------------------
    # CRUD APIs (write-capable)
    # --------------------------------------------------
    path(
        "crud/",
        include("invoices.views.v1.crud"),
    ),

    # --------------------------------------------------
    # Read-only APIs
    # --------------------------------------------------
    path(
        "read/",
        include("invoices.views.v1.read"),
    ),

    # --------------------------------------------------
    # UI helpers (autocomplete, UX)
    # --------------------------------------------------
    path(
        "ui/",
        include("invoices.views.v1.ui"),
    ),

    # --------------------------------------------------
    # Ops / admin-only APIs
    # --------------------------------------------------
    path(
        "ops/",
        include("invoices.views.v1.ops"),
    ),
]
