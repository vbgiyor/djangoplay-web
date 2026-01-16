import logging

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class APIRequestLoggingMiddleware(MiddlewareMixin):

    """
    Persists API request metadata for auditing and analytics.

    Important:
    - This middleware must NEVER block or fail a request
    - Authentication is best-effort only
    - DB errors are swallowed by design

    """

    API_PREFIXES = ("/api/", "/console/")
    METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}

    def process_response(self, request, response):
        try:
            if (
                request.method in self.METHODS
                and request.path.startswith(self.API_PREFIXES)
            ):
                user = getattr(request, "user", None)

                # Best-effort JWT resolution (no failure propagation)
                if not user or not getattr(user, "is_authenticated", False):
                    try:
                        from rest_framework_simplejwt.authentication import JWTAuthentication

                        authenticator = JWTAuthentication()
                        auth_result = authenticator.authenticate(request)
                        if auth_result:
                            user, _ = auth_result
                    except Exception:
                        pass

                from apidocs.models.apirequestlog import APIRequestLog

                APIRequestLog.objects.create(
                    user=user if getattr(user, "is_authenticated", False) else None,
                    path=request.path,
                    method=request.method,
                    response_status=getattr(response, "status_code", None),
                    client_ip=getattr(request, "client_ip", None),
                    user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                )

        except Exception as exc:
            logger.error(
                "APIRequestLoggingMiddleware failed",
                exc_info=exc,
            )

        return response
