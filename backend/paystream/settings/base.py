"""
Base settings for DjangoPlay.
Shared across development, staging, and production.
Environment-specific settings override these in dev.py, staging.py, prod.py.
"""

# ---------------------------------------------------------------------
# LOAD CORE APP SETTINGS FIRST
# ---------------------------------------------------------------------
from django.conf import settings

from paystream.app_settings.cache import *
from paystream.app_settings.celery import *
from paystream.app_settings.common import *
from paystream.app_settings.core import *
from paystream.app_settings.database import *
from paystream.app_settings.drf_spectacular import SPECTACULAR_SETTINGS
from paystream.app_settings.email import *
from paystream.app_settings.jwt import *
from paystream.app_settings.link_expiry import *
from paystream.app_settings.logging import *
from paystream.app_settings.middleware import *
from paystream.app_settings.rest_framework import *
from paystream.app_settings.security import *
from paystream.app_settings.site import *
from paystream.app_settings.static_media import *
from paystream.app_settings.templates import *
from paystream.app_settings.werkzeug import *
from paystream.settings.validation import *

# Default; overridden by dev/staging/prod
DEBUG = False

# Spectacular schema visibility
SPECTACULAR_SETTINGS["SERVE_INCLUDE_SCHEMA"] = DEBUG


# ---------------------------------------------------------------------
# SITE CONFIG (MUST LOAD *BEFORE* ALLAUTH IMPORT)
# ---------------------------------------------------------------------
SITE_PROTOCOL = get_decrypted_value("SITE_PROTOCOL", default="https").strip()
SITE_HOST     = get_decrypted_value("SITE_HOST", default="localhost").strip()
SITE_PORT     = get_decrypted_value("SITE_PORT", default="").strip()

# Canonical SITE_URL
SITE_URL = build_site_url(SITE_PROTOCOL, SITE_HOST, SITE_PORT)

# ---------------------------------------------------------------------
# GOOGLE OAUTH (must load AFTER SITE_PROTOCOL is known)
# ---------------------------------------------------------------------

if SITE_PROTOCOL == "https":
    GOOGLE_CLIENT_ID = get_decrypted_value("GOOGLE_CLIENT_ID_HTTPS")
    GOOGLE_CLIENT_SECRET = get_decrypted_value("GOOGLE_CLIENT_SECRET_HTTPS")
else:
    GOOGLE_CLIENT_ID = get_decrypted_value("GOOGLE_CLIENT_ID_HTTP")
    GOOGLE_CLIENT_SECRET = get_decrypted_value("GOOGLE_CLIENT_SECRET_HTTP")

# export for use in allauth + runtime setup
settings.GOOGLE_CLIENT_ID = GOOGLE_CLIENT_ID
settings.GOOGLE_CLIENT_SECRET = GOOGLE_CLIENT_SECRET

# ---------------------------------------------------------------------
# NOW IMPORT ALLAUTH SETTINGS (THE FIX)
# ---------------------------------------------------------------------
from paystream.app_settings.allauth import *

# ---------------------------------------------------------------------
# SETTINGS VALIDATION
# ---------------------------------------------------------------------
validate_settings(
    SITE_PROTOCOL=SITE_PROTOCOL,
    SITE_HOST=SITE_HOST,
    SITE_PORT=SITE_PORT,
    SECRET_KEY=SECRET_KEY,
)


# ---------------------------------------------------------------------
# CELERY CONFIGURATION (LAST)
# ---------------------------------------------------------------------
try:
    from paystream.app_settings.celery import configure_celery_settings
    configure_celery_settings(globals())
except Exception as e:
    raise RuntimeError(f"Celery settings failed to load: {e}")
