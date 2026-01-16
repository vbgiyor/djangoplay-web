from drf_spectacular.utils import OpenApiResponse, extend_schema


class BaseSchema:
    # This is the core description that applies to all actions (exception handling, throttling, pagination, etc.)
    common_description = """
        - App-level exception handling via `error_class`
        - Throttling, filtering, pagination
        - Standard CRUD logging and cache invalidation
    """

    # Caching description, only relevant to views with caching
    caching_description = """
        - Caching enabled for this view
    """

    @classmethod
    def get_common_schema(cls, summary, description, serializer_class, operation_id=None, include_cache=True, many=True):
        """
        Generate a common schema that can be reused across different views.

        Args:
            summary: The summary of the API view.
            description: A detailed description of the API view.
            serializer_class: The serializer class used for the response.
            operation_id: The unique operation ID for the API method (optional).
            include_cache: Whether or not to include the caching description.
            many: Whether the serializer should be treated as a list (True) or single object (False).

        Returns:
            The schema with common documentation details.

        """
        # Always include the core descriptions
        final_description = description + cls.common_description

        # Append caching description if enabled
        if include_cache:
            final_description += cls.caching_description

        schema_kwargs = {
            'summary': summary,
            'description': final_description,
            'responses': {
                200: OpenApiResponse(
                    description="Success",
                    response=serializer_class(many=many) if many else serializer_class
                ),
                400: OpenApiResponse(description="Invalid input"),
                401: OpenApiResponse(description="Unauthorized"),
                403: OpenApiResponse(description="Permission denied"),
                404: OpenApiResponse(description="Not found"),
                500: OpenApiResponse(description="Server error"),
            },
        }

        # Only add operation_id if it is provided
        if operation_id:
            schema_kwargs['operation_id'] = operation_id

        return extend_schema(**schema_kwargs)

    @classmethod
    def get_write_schema(
        cls,
        summary,
        description,
        request_serializer,
        response_serializer,
        operation_id=None,
    ):
        final_description = description + cls.common_description

        return extend_schema(
            summary=summary,
            description=final_description,
            request=request_serializer,
            responses={
                200: OpenApiResponse(
                    description="Success",
                    response=response_serializer,
                ),
                400: OpenApiResponse(description="Invalid input"),
                401: OpenApiResponse(description="Unauthorized"),
                403: OpenApiResponse(description="Permission denied"),
                404: OpenApiResponse(description="Not found"),
                500: OpenApiResponse(description="Server error"),
            },
            operation_id=operation_id,
        )
