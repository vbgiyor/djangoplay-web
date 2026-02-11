from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from frontend.views import *

from paystream.custom_site.admin_site import admin_site

# from users.views.auth import (
#     CustomTokenObtainPairView, CSRFTokenView, CustomTokenRefreshView, AuthLogView, RedocTokenVerifyView
# )
from paystream.custom_site.custom_admin_views import app_index_view, custom_changelist_view, single_app_view

# -----------------------------------------------------------------
# HANDLER SETTINGS – MUST BE AT THE TOP-LEVEL urls.py
# -----------------------------------------------------------------

handler403 = custom_403
handler401 = custom_401
handler404 = custom_404

# -----------------------------------------------------------------
# 2. URL configuration
# -----------------------------------------------------------------

urlpatterns = [
    # ------------------------------------------------------------------
    # Authentication Routes (must come before allauth.urls)
    # ------------------------------------------------------------------
    path("accounts/login/", ConsoleLoginView.as_view(), name="account_login"),
    path(
        "accounts/password/reset/",
        CustomPasswordResetView.as_view(),
        name="account_reset_password",
    ),

    # Preferred first
    # path(
    #     "accounts/password/reset/key/<uidb36>/<key>/",
    #     CustomPasswordResetConfirmView.as_view(),
    #     name="account_reset_password_from_key",
    # ),
    path(
        "accounts/password/reset/<str:token>/",
        CustomPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),


    # Legacy fallback (currently disabled)
    # path("accounts/password/reset/key/<uidb36>-<key>/", CustomPasswordResetConfirmView.as_view(), name="account_reset_password_from_key_dash"),

    path("accounts/logout/", CustomLogoutView.as_view(), name="account_logout"),

    # API to handle Google SSO cancel redirection
    path(
        "accounts/3rdparty/login/cancelled/",
        social_login_cancelled_view,
        name="socialaccount_login_cancelled",
    ),

    # ------------------------------------------------------------------
    # Allauth routes
    # ------------------------------------------------------------------
    path("accounts/", include("allauth.urls")),

    # ------------------------------------------------------------------
    # API Routes for Users app (must come before allauth for signups/verification)
    # ------------------------------------------------------------------
    path("users/", include("users.urls")),

    # ------------------------------------------------------------------
    # Main API Routes
    # ------------------------------------------------------------------
    path("api/v1/helpdesk/", include("helpdesk.urls")),
    path("api/v1/teamcentral/", include("teamcentral.urls")),
    path("api/v1/locations/", include("locations.urls")),
    path("api/v1/industries/", include("industries.urls")),
    path("api/v1/fincore/",include("fincore.urls")),
    path("api/v1/entities/", include(("entities.urls"))),
    path("api/v1/invoices/", include("invoices.urls")),
    path("api/v1/", include("apidocs.urls")),

    # ------------------------------------------------------------------
    # JWT / Auth Token Endpoints
    # ------------------------------------------------------------------
    # path("api/v1/auth/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    # path("api/v1/auth/token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    # path("api/v1/auth/log/", AuthLogView.as_view(), name="auth_log"),
    # path("api/v1/auth/verify/", RedocTokenVerifyView.as_view()),
    # path("api/v1/auth/csrf/", CSRFTokenView.as_view(), name="csrf_token"),

    # ------------------------------------------------------------------
    # Users Auth API (JWT, CSRF, audit)
    # ------------------------------------------------------------------
    path("api/v1/auth/", include("users.views.v1.auth")),

    # ------------------------------------------------------------------
    # Frontend & Console Routes
    # ------------------------------------------------------------------
    path("api/v1/", include("frontend.urls")),
    path("console/dashboard/", dashboard_view, name="console_dashboard"),
    path("support/", support_view, name="support"),

    # ------------------------------------------------------------------
    # Custom Admin Console Routes
    # ------------------------------------------------------------------
    path(
        "console/<str:app_label>/<str:model_name>/",
        custom_changelist_view,
        name="admin_custom_changelist",
    ),
    path("admin/<str:app_label>/", single_app_view, name="admin_single_app"),
    path("console/", admin_site.urls),
    path("admin/", app_index_view, name="admin_app_index"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
