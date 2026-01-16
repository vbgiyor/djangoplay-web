import uuid
from contextvars import ContextVar

# Async-safe request context
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIDMiddleware:

    """
    Attaches a request_id to every incoming HTTP request.

    - Reuses X-Request-ID if provided by upstream (LB / Gateway)
    - Generates UUID otherwise
    - Exposes request.request_id
    - Echoes X-Request-ID in response headers

    This middleware MUST be early in the chain.
    """

    HEADER_NAME = "HTTP_X_REQUEST_ID"
    RESPONSE_HEADER = "X-Request-ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming_request_id = request.META.get(self.HEADER_NAME)
        request_id = incoming_request_id or str(uuid.uuid4())

        token = request_id_var.set(request_id)
        request.request_id = request_id

        try:
            response = self.get_response(request)
            response[self.RESPONSE_HEADER] = request_id
            return response
        finally:
            request_id_var.reset(token)
