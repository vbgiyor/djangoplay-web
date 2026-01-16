import logging

from apidocs.utils.querysanitizer import add_sanitization_filter_to_logger
from django.db.models import Q

from .base import BaseFilterMixin

logger = logging.getLogger(__name__)
add_sanitization_filter_to_logger(logger)

class TrigramSearchFilterMixin(BaseFilterMixin):

    """
    Applies trigram search using `?search=` query param.

    Child classes must define:
        search_fields_trigram = ["field1", "field2"]
    """

    search_param = "search"
    search_fields_trigram = []

    def apply_trigram_search(self, queryset):
        search = self.request.query_params.get(self.search_param)
        if not search or not self.search_fields_trigram:
            return queryset

        q = Q()
        for field in self.search_fields_trigram:
            q |= Q(**{f"{field}__trigram_similar": search})

        logger.debug(
            "[TrigramSearch] model=%s search=%s fields=%s",
            queryset.model.__name__,
            search,
            self.search_fields_trigram,
        )

        return queryset.filter(q)
