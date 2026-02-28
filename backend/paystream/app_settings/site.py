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

