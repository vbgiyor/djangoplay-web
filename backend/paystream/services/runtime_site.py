import logging

from django.conf import settings
from django.contrib.sites.models import Site

logger = logging.getLogger(__name__)

_initialized = False


def ensure_runtime_site():
    global _initialized
    if _initialized:
        return
    _initialized = True

    host = settings.SITE_HOST
    port = settings.SITE_PORT

    domain = f"{host}:{port}" if port and port not in ("80", "443", "") else host
    if len(domain) > 100:
        raise ValueError(
            f"Computed Site.domain '{domain}' exceeds 100 characters. "
            f"Check decrypted SITE_HOST / SITE_PORT values."
        )

    site, created = Site.objects.get_or_create(
        domain=domain,
        defaults={"name": domain},
    )

    settings.SITE_ID = site.id

    if created:
        logger.info(f"[Site] Created runtime Site: {domain}")
    else:
        logger.info(f"[Site] Using existing Site: {domain}")
