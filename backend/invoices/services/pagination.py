
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data: list[dict]) -> Response:
        """Add pagination metadata to response."""
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })

class CustomThrottle(UserRateThrottle):
    rate = '50/hour'

class CustomSearchThrottle(UserRateThrottle):
    rate = '100/hour'

