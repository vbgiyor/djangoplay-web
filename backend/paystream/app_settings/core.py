from django.core.exceptions import ImproperlyConfigured

from .common import get_decrypted_value

# ---------------------------------------------------------------------
# SECRET KEY (MANDATORY)
# ---------------------------------------------------------------------
SECRET_KEY = get_decrypted_value("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in encrypted .env")

# SECRET_KEY = "temporary-insecure-key-for-debugging-only"

# ---------------------------------------------------------------------
# CORE APPLICATION CONFIG
# ---------------------------------------------------------------------
INSTALLED_APPS = [
    "mptt",
    "dal",
    "dal_select2",

    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "django.contrib.sites",
    "django.contrib.humanize",
    "django_extensions",

    "drf_spectacular",

    # Internal apps
    "audit",
    "policyengine.apps.PolicyengineConfig",
    "frontend",
    "apidocs",
    "paystream.apps.PaystreamConfig",
    "fincore.apps.FincoreConfig",
    "devtools",
    "rest_framework",
    "core.apps.CoreConfig",
    "utilities.apps.UtilitiesConfig",
    "mailer",
    "users.apps.UsersConfig",
    "locations.apps.LocationsConfig",
    "industries",
    "entities.apps.EntitiesConfig",
    "invoices",

    # Auth / OAuth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",

    # History / JWT
    "rest_framework_simplejwt.token_blacklist",
    "simple_history",

    # Styling / inline CSS / compressor
    "django_inlinecss",
    "compressor",
]

# Custom User Model
AUTH_USER_MODEL = "users.Employee"

ROOT_URLCONF = "paystream.urls"
WSGI_APPLICATION = "paystream.wsgi.application"
ASGI_APPLICATION = "paystream.asgi.application"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "en-IN"
USE_I18N = True
USE_TZ = True
TIME_ZONE = "Asia/Kolkata"

INTERNAL_IPS = ["127.0.0.1", "localhost"]


# ---------------------------------------------------------------------
# HUMAN-FRIENDLY APP DISPLAY NAMES FOR ADMIN UI
# ---------------------------------------------------------------------
APP_DISPLAY_NAMES = {
    "users": "Users Catalogue",
    "locations": "Geographies",
    "industries": "Industries",
    "fincore": "Finance",
    "entities": "Businesses",
    "invoices": "Invoices & Billing",
    "audit": "Logging Journal",
}

APPS_READY = {
    "invoices": True,
    "fincore": False,
    "users": True,
    "locations": True,
    "industries": True,
    "entities": True,
    "audit": True,
}
