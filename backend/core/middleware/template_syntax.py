import logging

from django.template import TemplateSyntaxError

logger = logging.getLogger("django.template")

class TemplateSyntaxErrorLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except TemplateSyntaxError:
            logger.critical(
                "TEMPLATE SYNTAX ERROR",
                extra={"path": request.path},
            )
            raise
