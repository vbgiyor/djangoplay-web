import logging

from django.conf import settings
from django.urls import Resolver404, get_resolver, resolve

logger = logging.getLogger(__name__)


class URLResolutionLoggingMiddleware:

    """
    DEBUG-ONLY middleware for URL diagnostics.

    DO NOT ENABLE IN PRODUCTION.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            resolved = resolve(request.path_info)
            logger.debug(
                "Resolved URL path=%s view=%s namespace=%s",
                request.path_info,
                resolved.view_name,
                resolved.namespace,
            )
        except Resolver404:
            logger.debug("URL resolution failed for path=%s", request.path_info)
        except Exception:
            logger.exception("Unexpected error during URL resolution")

        # Optional conflict detection
        resolver = get_resolver()
        matches = [
            str(p.pattern)
            for p in resolver.url_patterns
            if hasattr(p, "pattern") and p.pattern.match(request.path_info)
        ]

        if len(matches) > 1:
            logger.warning(
                "Potential URL conflict path=%s patterns=%s",
                request.path_info,
                matches,
            )

        return self.get_response(request)


if not settings.DEBUG:
    raise RuntimeError(
        "URLResolutionLoggingMiddleware must not be enabled outside DEBUG"
    )
