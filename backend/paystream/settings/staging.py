import os

from .base import *

DEBUG = False

ALLOWED_HOSTS = [
    "*",
    "localhost",
    "127.0.0.1",
    "issues.localhost",
    "docs.localhost"
]

# Load from encrypted env or fallback
if not SITE_HOST:
    SITE_HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME", "")

SITE_URL = build_site_url(SITE_PROTOCOL, SITE_HOST, SITE_PORT)

# Secure but no HSTS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
