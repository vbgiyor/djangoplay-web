from django.conf import settings

from .common import get_decrypted_value
from .link_expiry import EMAIL_VERIFICATION_EXPIRE_DAYS

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Social Apps configs
GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET

# Allauth Redirection and core configs
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_ADAPTER = "users.adapters.accounts.social.CustomSocialAccountAdapter"
# ACCOUNT_LOGIN_REDIRECT_URL = '/console/dashboard/'
# ACCOUNT_LOGOUT_REDIRECT_URL = "/console/login/"


# Determine protocol without relying on Django settings (fix for early imports)
ACCOUNT_DEFAULT_HTTP_PROTOCOL = get_decrypted_value(
    "SITE_PROTOCOL",
    default="https"
).strip()

ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_ADAPTER = "users.adapters.accounts.custom.CustomAccountAdapter"
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = EMAIL_VERIFICATION_EXPIRE_DAYS
# Email settings
ACCOUNT_EMAIL_SUBJECT_PREFIX = f'[{get_decrypted_value("SITE_NAME", "")}] '  # Dynamic prefix using SITE_NAME

# SOCIALACCOUNT_PROVIDERS = {
#     "google": {
#         "APP": {
#             "client_id": GOOGLE_CLIENT_ID,
#             "secret": GOOGLE_CLIENT_SECRET,
#         },
#         "SCOPE": ["profile", "email"],
#         "AUTH_PARAMS": {
#             "access_type": "online",
#             "response_type": "code",
#         },
#         "REDIRECT_URL": f"{getattr(settings, 'SITE_URL', 'localhost:3333')}/accounts/google/login/callback/",
#     }
# }

# Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_RESET_TIMEOUT = EMAIL_VERIFICATION_EXPIRE_DAYS * 24 * 3600
