from django.urls import path
from django.views.generic import TemplateView

from .views import *

app_name = "frontend"

urlpatterns = [
    # ------------------------------------------------------------------
    # Signup / SSO onboarding
    # ------------------------------------------------------------------
    # Manual email/password signup (your custom flow)
    path(
        "accounts/manual-signup/",
        ManualSignupView.as_view(),
        name="manual_signup",
    ),

    # Allauth signup (SSO / social)
    path(
        "accounts/signup/",
        CustomSignupView.as_view(),
        name="allauth_signup",
    ),

    # Email verification (GET only)
    path(
        "accounts/verify/",
        UnifiedEmailVerifyView.as_view(),
        name="account_verify",
    ),
    path(
        "accounts/resend-verification/",
        ResendVerificationView,
        name="accounts_resend_verification",
    ),


    # ------------------------------------------------------------------
    # License pages
    # ------------------------------------------------------------------
    path(
        "license/",
        TemplateView.as_view(template_name="account/site_pages/license.html"),
        name="license",
    ),
    path("license/file/", license_file_view, name="license_file"),

    # ------------------------------------------------------------------
    # Unified API login (Swagger / ReDoc)
    # ------------------------------------------------------------------
    path("accounts/api-login/", ApiLoginView.as_view(), name="api_login"),
    path("accounts/api/", ApiLoginView.as_view(), name="api_console"),      # For Swagger
    path("accounts/redoc/", ApiLoginView.as_view(), name="redoc_console"),  # For ReDoc

    # ------------------------------------------------------------------
    # Report bug
    # ------------------------------------------------------------------
    path("report-bug/", ReportBugView.as_view(), name="report_bug"),

    # ------------------------------------------------------------------
    # Unsubscribe
    # ------------------------------------------------------------------
    path(
        "unsubscribe/<str:uidb64>/<str:token>/",
        UnsubscribeView.as_view(),
        name="unsubscribe",
    ),
    path("unsubscribe/", UnsubscribeView.as_view(), name="unsubscribe_manual"),

    # ------------------------------------------------------------------
    # “Who am I?” endpoints
    # ------------------------------------------------------------------
    path("auth/me/", SessionUserMeView.as_view(), name="session-user-me"),
    path("auth/me/jwt/", UserMeView.as_view(), name="user-me-jwt"),
]
