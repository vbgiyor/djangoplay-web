import logging
from datetime import datetime

from apidocs.utils.base_schema import BaseSchema
from apidocs.utils.querysanitizer import add_sanitization_filter_to_logger
from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from utilities.api.generic_views import BaseListAPIView
from utilities.api.pagination import StandardResultsSetPagination
from utilities.api.rate_limits import CustomThrottle

from industries.exceptions import InvalidIndustryData
from industries.models import Industry
from industries.serializers import IndustryReadSerializerV1

logger = logging.getLogger(__name__)
add_sanitization_filter_to_logger(logger)


@extend_schema(tags=["Industries"])
class IndustryListAPIView(BaseListAPIView):

    """
    API View to list Industries with advanced filtering.
    Includes:
    - pagination
    - filtering by code, level, sector, parent, created_at (range)
    - simple caching keyed by query params
    """

    pagination_class = StandardResultsSetPagination
    throttle_classes = [CustomThrottle]
    queryset = Industry.objects.filter(deleted_at__isnull=True)
    serializer_class = IndustryReadSerializerV1
    error_class = InvalidIndustryData
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['code', 'level', 'sector', 'parent']
    ordering_fields = ['id', 'code', 'level']
    search_fields = ['code', 'description']
    cache_timeout = 3600  # 1 hour; adjust as needed

    @BaseSchema.get_common_schema(
        "List Industries (ListAPIView).",
        """
        - This endpoint allows you to list industries.
        - You can filter by:
            * code
            * level
            * sector
            * parent
            * created_after / created_before (YYYY-MM-DD)
        """,
        serializer_class=IndustryReadSerializerV1
    )
    def get(self, request, *args, **kwargs):
        """
        Handle GET requests for Industry list.
        Includes query param filtering, caching, and pagination.
        """
        query_params = request.query_params.dict()
        query_hash = hash(frozenset(query_params.items()))
        cache_key = f"industries_filters_{query_hash}"
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.info(f"Cache hit for industries with filters {query_params}")
            return Response(cached_data)

        # Get filtered queryset
        queryset = self.get_queryset()

        # If no records, return empty result with message
        if not queryset.exists():
            logger.info(f"No industries found with filters {query_params}")
            return Response({"results": [], "detail": "No industries found."})

        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            cache.set(cache_key, paginated_response.data, timeout=self.cache_timeout)
            logger.info(f"Cache set (paginated) for industries with filters {query_params}")
            return paginated_response

        # Non-paginated
        serializer = self.get_serializer(queryset, many=True)
        serialized_data = serializer.data
        cache.set(cache_key, serialized_data, timeout=self.cache_timeout)
        logger.info(f"Cache set (non-paginated) for industries with filters {query_params}")
        return Response(serialized_data)

    def get_queryset(self):
        """
        Custom filtering logic for industries:
        - code exact
        - level exact with validation
        - sector exact with validation
        - parent id
        - created_after / created_before (YYYY-MM-DD)
        """
        queryset = super().get_queryset()
        params = self.request.query_params

        # Filter by code
        code = params.get('code')
        if code:
            queryset = queryset.filter(code=code)

        # Filter by level
        level = params.get('level')
        if level:
            valid_levels = {choice[0] for choice in Industry.LEVEL_CHOICES}
            if level not in valid_levels:
                logger.warning(f"Invalid level in IndustryListAPIView: {level}")
                raise self.error_class(
                    f"Invalid level: {level}",
                    code="invalid_level",
                    details={"field": "level", "value": level, "valid_choices": list(valid_levels)}
                )
            queryset = queryset.filter(level=level)

        # Filter by sector
        sector = params.get('sector')
        if sector:
            valid_sectors = {choice[0] for choice in Industry.SECTOR_CHOICES}
            if sector not in valid_sectors:
                logger.warning(f"Invalid sector in IndustryListAPIView: {sector}")
                raise self.error_class(
                    f"Invalid sector: {sector}",
                    code="invalid_sector",
                    details={"field": "sector", "value": sector, "valid_choices": list(valid_sectors)}
                )
            queryset = queryset.filter(sector=sector)

        # Filter by parent id
        parent = params.get('parent')
        if parent:
            try:
                parent_id = int(parent)
                queryset = queryset.filter(parent__id=parent_id)
            except ValueError:
                logger.warning(f"Invalid parent id in IndustryListAPIView: {parent}")
                raise self.error_class(
                    f"Invalid parent id: {parent}",
                    code="invalid_fields",
                    details={"field": "parent", "value": parent}
                )

        # Filter by created_at range
        created_after = params.get('created_after')
        if created_after:
            try:
                created_after_date = datetime.strptime(created_after, "%Y-%m-%d")
                queryset = queryset.filter(created_at__gte=created_after_date)
            except ValueError:
                logger.warning(f"Invalid date format for created_after: {created_after}")
                raise self.error_class(
                    f"Invalid date format for created_after: {created_after}",
                    code="invalid_fields",
                    details={"field": "created_after", "value": created_after}
                )

        created_before = params.get('created_before')
        if created_before:
            try:
                created_before_date = datetime.strptime(created_before, "%Y-%m-%d")
                queryset = queryset.filter(created_at__lte=created_before_date)
            except ValueError:
                logger.warning(f"Invalid date format for created_before: {created_before}")
                raise self.error_class(
                    f"Invalid date format for created_before: {created_before}",
                    code="invalid_fields",
                    details={"field": "created_before", "value": created_before}
                )

        return queryset
