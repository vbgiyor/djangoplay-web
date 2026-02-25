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


# import logging

# from django.conf import settings
# from django.contrib.sites.models import Site

# logger = logging.getLogger(__name__)


# def ensure_runtime_site():
#     """
#     Ensure a Site object exists matching the current runtime
#     SITE_HOST + SITE_PORT and set settings.SITE_ID accordingly.

#     Safe to call multiple times.
#     """

#     host = getattr(settings, "SITE_HOST", None)
#     port = getattr(settings, "SITE_PORT", None)

#     if not host:
#         raise RuntimeError("SITE_HOST is not configured.")

#     domain = (
#         f"{host}:{port}"
#         if port and port not in ("80", "443", "")
#         else host
#     )

#     if len(domain) > 100:
#         raise ValueError(
#             f"Computed Site.domain '{domain}' exceeds 100 characters. "
#             "Check SITE_HOST / SITE_PORT values."
#         )

#     site, created = Site.objects.get_or_create(
#         domain=domain,
#         defaults={"name": domain},
#     )

#     # Always ensure SITE_ID matches the runtime site
#     if getattr(settings, "SITE_ID", None) != site.id:
#         settings.SITE_ID = site.id

#     if created:
#         logger.info(f"[Site] Created runtime Site: {domain} (id={site.id})")
#     else:
#         logger.info(f"[Site] Active Site: {domain} (id={site.id})")
