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

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def get_site_base_url(request=None) -> str:
    """
    Returns the canonical site base URL (no trailing slash).
    Priority:
      1. HttpRequest  → always authoritative for request-scoped code
      2. settings.SITE_URL → decrypted at Django startup via common.py
      3. settings fallback → build from SITE_PROTOCOL + SITE_HOST + SITE_PORT
    """
    # 1. HttpRequest → always correct
    if request is not None:
        return request.build_absolute_uri("/").rstrip("/")

    # 2. settings.SITE_URL — already decrypted by get_decrypted_value()
    #    Never read os.getenv("SITE_URL") directly: it holds raw ciphertext.
    site_url = getattr(settings, "SITE_URL", "").strip()
    if site_url:
        return site_url.rstrip("/")

    # 3. Fallback — build from parts (also decrypted via settings)
    protocol = getattr(settings, "SITE_PROTOCOL", "https")
    host     = getattr(settings, "SITE_HOST", "localhost")
    port     = str(getattr(settings, "SITE_PORT", "9999"))

    base = f"{protocol}://{host}"
    if port and port not in ("80", "443", ""):
        base += f":{port}"

    logger.debug("get_site_base_url: using settings fallback → %s", base)
    return base
