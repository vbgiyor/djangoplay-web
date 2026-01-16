from apidocs.utils.helper import file_response
from drf_spectacular.utils import extend_schema


def file_download_endpoint(
    description: str = "File download",
    content_type: str | None = None,
    extra_responses: dict | None = None
):
    """
    Decorator to mark a CBV as a file download endpoint for DRF Spectacular.

    Args:
        description: Description for the file download.
        content_type: MIME type of the file (e.g., "text/csv", "application/pdf").
        extra_responses: Optional additional responses (e.g., {401: file_response(...)}).

    Usage:
        @file_download_endpoint(
            "CSV with city data",
            content_type="text/csv",
            extra_responses={401: file_response("Unauthorized")}
        )
        class CityExportAPIView(APIView):
            ...

    """
    def decorator(view_cls):
        # Build the responses dict
        responses = {200: file_response(description, content_type)}
        if extra_responses:
            responses.update(extra_responses)

        # Apply extend_schema dynamically
        return extend_schema(responses=responses)(view_cls)

    return decorator
