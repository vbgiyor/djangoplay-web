from datetime import datetime

from .base import BaseFilterMixin


class DateRangeFilterMixin(BaseFilterMixin):

    """
    Adds support for:
      ?created_after=YYYY-MM-DD
      ?created_before=YYYY-MM-DD
    """

    date_field = "created_at"  # override if needed

    def apply_date_range_filter(self, queryset):
        params = self.request.query_params

        created_after = params.get("created_after")
        if created_after:
            try:
                queryset = queryset.filter(
                    **{f"{self.date_field}__gte": datetime.strptime(created_after, "%Y-%m-%d")}
                )
            except ValueError:
                self.raise_invalid("created_after", created_after)

        created_before = params.get("created_before")
        if created_before:
            try:
                queryset = queryset.filter(
                    **{f"{self.date_field}__lte": datetime.strptime(created_before, "%Y-%m-%d")}
                )
            except ValueError:
                self.raise_invalid("created_before", created_before)

        return queryset
