from .base import *

DEBUG = True

ALLOWED_HOSTS = [
    "*",
    "localhost",
    "127.0.0.1",
    "issues.localhost",
    "docs.localhost"
]

# Runtime overrides from zshrc (devssl, devhttp)
from paystream.app_settings.common import get_decrypted_value

proto_env = get_decrypted_value("SITE_PROTOCOL")
host_env  = get_decrypted_value("SITE_HOST")
port_env  = get_decrypted_value("SITE_PORT")

# Always use decrypted values from common.py
SITE_PROTOCOL = proto_env or "http"
SITE_HOST     = host_env or "localhost"
SITE_PORT     = port_env or ""

# Django-extensions runserver_plus (optional)
try:
    import werkzeug  # noqa
    RUNSERVER_PLUS_AVAILABLE = True
except Exception:
    RUNSERVER_PLUS_AVAILABLE = False

SITE_URL = build_site_url(SITE_PROTOCOL, SITE_HOST, SITE_PORT)

# Disable secure cookies in dev
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = None

# EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
