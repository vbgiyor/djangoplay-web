import os

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse


def get_admin_url(instance, request=None):
    """
    Return full admin URL for a model instance.

    - Uses Django's ContentType + admin change URL.
    - Uses get_site_base_url() for base URL (so same http/https logic
      as password reset and other links).
    """
    ct = ContentType.objects.get_for_model(instance)
    path = reverse(f"admin:{ct.app_label}_{ct.model}_change", args=[instance.pk])

    base_url = get_site_base_url()
    print(">>>", f"{base_url}{path}")
    return f"{base_url}{path}"


def get_site_base_url(request=None):
    """
    Critical fix: Correct priority + use localhost, not 127.0.0.1
    """
    # 1. HttpRequest → always correct[](https://localhost:9999)
    if request is not None:
        return request.build_absolute_uri("/").rstrip("/")

    # 2. Celery / tasks → respect explicit SITE_URL (set by devssl)
    site_url = os.getenv("SITE_URL")
    if site_url:
        return site_url.rstrip("/")

    # 3. Fallback → build from settings
    protocol = getattr(settings, "SITE_PROTOCOL", "https")
    host = getattr(settings, "SITE_HOST", "localhost")
    port = getattr(settings, "SITE_PORT", "9999")

    base = f"{protocol}://{host}"
    if port and port not in ("80", "443", ""):
        base += f":{port}"
    return base
