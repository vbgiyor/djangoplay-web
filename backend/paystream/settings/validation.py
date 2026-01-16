from django.core.exceptions import ImproperlyConfigured


def validate_settings(SITE_PROTOCOL, SITE_HOST, SITE_PORT, SECRET_KEY):
    if SITE_PROTOCOL not in ("http", "https"):
        raise ImproperlyConfigured(f"Invalid SITE_PROTOCOL={SITE_PROTOCOL}")

    if not SITE_HOST:
        raise ImproperlyConfigured("SITE_HOST must be provided")

    if SITE_PORT and not SITE_PORT.isdigit():
        raise ImproperlyConfigured("SITE_PORT must be numeric")

    if not SECRET_KEY:
        raise ImproperlyConfigured("SECRET_KEY is missing")

    return True
