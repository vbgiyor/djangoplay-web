import os

from .base import *

DEBUG = False

ALLOWED_HOSTS = [
    "djangoplay.org",
    "www.djangoplay.org",
    "*.djangoplay.org",
    "localhost",
    "127.0.0.1",
]

PARENT_HOST = "djangoplay.org"

# Render hostname fallback
if not SITE_HOST:
    SITE_HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME", "")

SITE_URL = build_site_url(SITE_PROTOCOL, SITE_HOST, SITE_PORT)

# Fully secure production configuration
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
