from .base import BaseFilterMixin


class ForeignKeyFilterMixin(BaseFilterMixin):

    """
    Adds support for filtering by foreign key IDs.

    Example:
      self.apply_fk_filter(qs, "country", param="country_id")

    """

    def apply_fk_filter(self, queryset, field: str, param: str = None):
        param = param or f"{field}_id"
        value = self.kwargs.get(param) or self.request.query_params.get(param)

        if not value:
            return queryset

        try:
            return queryset.filter(**{f"{field}_id": int(value)})
        except (TypeError, ValueError):
            self.raise_invalid(param, value)
