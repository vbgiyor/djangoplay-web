from django.urls import include, path
from paystream.urlconf.base import urlpatterns as base_urlpatterns

urlpatterns = [
    *base_urlpatterns,

    # ----------------------------------------------------------
    # Issue Tracker UI (Subdomain: issues.*)
    # Proper namespace registration required for reverse("issues:list")
    # ----------------------------------------------------------
    path(
        "",
        include(
            ("paystream.integrations.issuetracker.ui.urls", "issues"),
            namespace="issues",
        ),
    ),
]
