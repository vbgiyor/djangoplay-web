from contextvars import ContextVar

from core.request_context import client_ip

client_ip_var: ContextVar[str | None] = ContextVar("client_ip", default=None)


class ClientIPMiddleware:

    """
    Extracts client IP address and attaches it to request context.

    - Supports X-Forwarded-For
    - Async-safe via contextvars
    - No logging, no persistence
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")

        token = client_ip.set(ip)
        request.client_ip = ip

        try:
            return self.get_response(request)
        finally:
            client_ip.reset(token)

