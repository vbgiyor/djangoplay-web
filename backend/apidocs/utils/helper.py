from drf_spectacular.utils import OpenApiResponse, OpenApiTypes


def file_response(description: str = "File download", content_type: str | None = None) -> OpenApiResponse:
    """
    Helper to generate a DRF Spectacular response for any file download.

    Args:
        description: Description of the file download.
        content_type: Optional MIME type (e.g., "text/csv", "application/pdf").
                      If None, defaults to OpenApiTypes.BINARY.

    """
    # OpenApiTypes.BINARY already produces a valid binary schema (type=string, format=binary)
    # drf-spectacular does not allow 'content' as a keyword here.
    return OpenApiResponse(
        response=OpenApiTypes.BINARY,
        description=description,
    )
