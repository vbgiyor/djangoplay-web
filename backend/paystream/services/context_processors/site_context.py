from urllib.parse import urlparse

from django.conf import settings
from django.urls import reverse


def build_subdomain_url(subdomain: str, path: str) -> str:
    """
    Build absolute URL for a given subdomain and raw path.

    Example:
        build_subdomain_url("issues", "/issues/")
        -> https://issues.localhost:9999/issues/

    """
    parsed = urlparse(settings.SITE_URL)

    protocol = parsed.scheme
    host = parsed.hostname
    port = parsed.port

    full_host = f"{subdomain}.{host}"

    if port:
        domain = f"{protocol}://{full_host}:{port}"
    else:
        domain = f"{protocol}://{full_host}"

    return f"{domain}{path}"


def site_context(request):
    """
    Determine the authenticated user's default home URL
    based on the current request host (subdomain-aware).

    This allows the UI (e.g., logo links, home buttons)
    to dynamically resolve the correct landing page
    without embedding host logic inside templates.

    Rules:
        - issues.*  → /issues/
        - docs.*  → /docs/
        - default   → /console/dashboard/

    Returns:
        dict: {"HOME_URL": "<resolved-path>"}

    """
    SUBDOMAIN_HOME_MAP = {
        "issues": "issues:list",
        "console": "console_dashboard",
        "docs": "docs:index",
        # future:
        # "billing": "billing:dashboard",
        # "reports": "reports:home",
    }

    host = request.get_host().split(":")[0]
    parts = host.split(".")
    subdomain = parts[0] if len(parts) > 2 else None

    if subdomain in SUBDOMAIN_HOME_MAP:
        home_url = reverse(SUBDOMAIN_HOME_MAP[subdomain])
    else:
        home_url = reverse("console_dashboard")

    # Build issues subdomain absolute URL
    issues_tracker_url = build_subdomain_url("issues", "/issues/")
    docs_url = build_subdomain_url("docs", "/")

    return {
        "HOME_URL": home_url,
        "CURRENT_SUBDOMAIN": subdomain,
        "SITE_URL": settings.SITE_URL,
        "SITE_NAME": settings.SITE_NAME,
        "ISSUES_TRACKER_URL": issues_tracker_url,
        "DOCS_URL": docs_url,
        "WEBSITE_URL": getattr(settings, "WEBSITE_URL", "https://djangoplay.org/")
    }
