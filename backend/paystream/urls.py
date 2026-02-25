from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from frontend.views import *

from paystream.custom_site.admin_site import admin_site
from paystream.custom_site.custom_admin_views import (
    app_index_view,
    custom_changelist_view,
    single_app_view,
)

# -----------------------------------------------------------------
# HANDLER SETTINGS – MUST BE AT TOP LEVEL
# -----------------------------------------------------------------

handler403 = custom_403
handler401 = custom_401
handler404 = custom_404


# -----------------------------------------------------------------
# URL configuration
# -----------------------------------------------------------------
urlpatterns = [
    # ----------------------------------------------------------
    # Authentication Routes
    # ----------------------------------------------------------
    path("accounts/login/", ConsoleLoginView.as_view(), name="account_login"),
    path(
        "accounts/password/reset/",
        CustomPasswordResetView.as_view(),
        name="account_reset_password",
    ),
    path(
        "accounts/password/reset/<str:token>/",
        CustomPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("accounts/logout/", CustomLogoutView.as_view(), name="account_logout"),
    path(
        "accounts/3rdparty/login/cancelled/",
        social_login_cancelled_view,
        name="socialaccount_login_cancelled",
    ),

    # ----------------------------------------------------------
    # Allauth
    # ----------------------------------------------------------
    path("accounts/", include("allauth.urls")),

    # ----------------------------------------------------------
    # Users API
    # ----------------------------------------------------------
    path("users/", include("users.urls")),

    # ----------------------------------------------------------
    # Main APIs
    # ----------------------------------------------------------
    path("api/v1/helpdesk/", include("helpdesk.urls")),
    path("api/v1/teamcentral/", include("teamcentral.urls")),
    path("api/v1/locations/", include("locations.urls")),
    path("api/v1/industries/", include("industries.urls")),
    path("api/v1/fincore/", include("fincore.urls")),
    path("api/v1/entities/", include("entities.urls")),
    path("api/v1/invoices/", include("invoices.urls")),
    path("api/v1/", include("frontend.urls")),
    path("api/v1/", include("apidocs.urls")),

    # ----------------------------------------------------------
    # Users Auth API
    # ----------------------------------------------------------
    path("api/v1/auth/", include("users.views.v1.auth")),

    # ----------------------------------------------------------
    # Frontend & Console
    # ----------------------------------------------------------
    path("console/dashboard/", dashboard_view, name="console_dashboard"),
    path("support/", support_view, name="support"),

    # ----------------------------------------------------------
    # Generic Issue Tracker API (NOT UI)
    # ----------------------------------------------------------
    path(
        "api/v1/issuetracker/",
        include("paystream.integrations.issuetracker.urls"),
    ),

    # ----------------------------------------------------------
    # Admin Console
    # ----------------------------------------------------------
    path(
        "console/<str:app_label>/<str:model_name>/",
        custom_changelist_view,
        name="admin_custom_changelist",
    ),
    path("admin/<str:app_label>/", single_app_view, name="admin_single_app"),
    path("console/", admin_site.urls),
    path("admin/", app_index_view, name="admin_app_index"),
]

# ----------------------------------------------------------
# Serve MEDIA in DEBUG
# ----------------------------------------------------------
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
