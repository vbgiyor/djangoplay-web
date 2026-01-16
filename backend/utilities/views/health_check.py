import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger('health_check')


# Centralized simulated response definitions
HEALTH_RESPONSES = {
    200: {"status": "success", "message": "API is running", "version": "1.0.0"},
    404: {"status": "error", "message": "Not Found"},
    503: {"status": "error", "message": "Service Unavailable"},
    500: {"status": "error", "message": "Internal Server Error"},
    400: {"status": "error", "message": "Invalid status code requested"},
}

# Use these to define the OpenAPI schema dynamically
def _build_openapi_schema():
    schema = {}
    for code, example in HEALTH_RESPONSES.items():
        schema[code] = {
            "type": "object",
            "properties": {
                key: {"type": "string", "example": value}
                for key, value in example.items()
            },
        }
    return schema


@extend_schema(tags=["API Health Status"])
class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        auth=[],
        responses=_build_openapi_schema()
    )
    def get(self, request, *args, **kwargs):
        logger.debug(
            f"Health check requested by "
            f"{request.user if getattr(request, 'user', None) and request.user.is_authenticated else 'anonymous'}"
        )

        # Get status code from query parameter (defaults to 200)
        status_code = request.query_params.get("status_code", "200")

        try:
            code = int(status_code)
            if code in HEALTH_RESPONSES:
                return Response(HEALTH_RESPONSES[code], status=code)
            else:
                return Response(HEALTH_RESPONSES[400], status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            logger.error(f"Invalid status code requested: {status_code}")
            return Response(HEALTH_RESPONSES[400], status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}", exc_info=True)
            return Response(
                {"status": "error", "message": f"Health check failed: {str(e)}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
