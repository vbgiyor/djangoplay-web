from django.conf import settings

AUDIT_ADMIN_ROLES = getattr(
    settings,
    "AUDIT_ADMIN_ROLES",
    {"DJGO", "CEO", "CFO", "SSO"},
)
