import os
from pathlib import Path

# ---------------------------------------------------------------------
# SECRET KEY (MANDATORY, try env first, then ~/.dplay/.secrets)
# ---------------------------------------------------------------------
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '').strip()

if not SECRET_KEY:
    secrets_path = Path.home() / ".dplay" / ".secrets"
    if secrets_path.exists():
        with open(secrets_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DJANGO_SECRET_KEY="):
                    SECRET_KEY = line.split("=", 1)[1].strip()
                    break

if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY not found in environment or ~/.dplay/.secrets")

# ---------------------------------------------------------------------
# CORE APPLICATION CONFIG
# ---------------------------------------------------------------------
INSTALLED_APPS = [
    "mptt",
    "dal",
    "dal_select2",
    "django_hosts",

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
    "teamcentral",
    "helpdesk",
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
    "compressor",

    # Issue Tracker Integration
    "genericissuetracker",
    "paystream.integrations.issuetracker.apps.IssueTrackerIntegrationConfig",
    "paystream.integrations.issuetracker.ui",
]

# Custom User Model
AUTH_USER_MODEL = "users.Employee"

ROOT_URLCONF = "paystream.urlconf.default"
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
    "helpdek": "Help & Support",
    "teamcentral": "HR Catalogue",
}

APPS_READY = {
    "invoices": True,
    "fincore": False,
    "users": True,
    "locations": True,
    "industries": True,
    "entities": True,
    "audit": True,
    "helpdesk": True,
    "teamcentral": True,
}

# django-hosts config
ROOT_HOSTCONF = "paystream.hosts"
DEFAULT_HOST = "default"
