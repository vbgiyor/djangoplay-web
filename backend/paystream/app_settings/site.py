"""
Utility for dynamic SITE_URL computation across all environments.
"""

import logging

logger = logging.getLogger(__name__)


def build_site_url(protocol: str, host: str, port: str | None) -> str:
    """
    Build canonical SITE_URL based on protocol/host/port.
    Rules:
    - Protocol must be explicitly provided (http or https).
    - No fallback to https (that breaks devhttp).
    - Do not append port when it is blank, 80, or 443.
    """
    if not host:
        raise ValueError("SITE_HOST is required to compute SITE_URL")

    protocol = (protocol or "").strip().lower()
    if protocol not in ("http", "https"):
        raise ValueError(f"Invalid SITE_PROTOCOL '{protocol}' (expected 'http' or 'https')")

    if port in (None, "", "80", "443"):
        return f"{protocol}://{host}"

    return f"{protocol}://{host}:{port}"



def ensure_runtime_site(protocol: str, host: str, port: str):
    """
    Create/update Site entry at runtime using settings.SITE_HOST, SITE_PORT.
    Called from PaystreamConfig.ready().
    """
    if port and port not in ("80", "443", ""):
        domain = f"{host}:{port}"
    else:
        domain = host

    if len(domain) > 50:
        raise ValueError(f"Site.domain '{domain}' exceeds max_length=50")

    from django.contrib.sites.models import Site
    site, created = Site.objects.get_or_create(
        domain=domain,
        defaults={"name": domain},
    )

    if created:
        logger.info(f"[Site] Created site entry: {domain}")
    else:
        logger.info(f"[Site] Loaded site entry: {domain}")

    return site
