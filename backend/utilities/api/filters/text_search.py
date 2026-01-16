from .base import BaseFilterMixin


class NameSearchFilterMixin(BaseFilterMixin):

    """
    Adds support for:
      ?name=foo
    """

    name_field = "name"
    lookup = "icontains"  # can be overridden

    def apply_name_filter(self, queryset):
        value = self.request.query_params.get("name")
        if not value:
            return queryset

        lookup_expr = f"{self.name_field}__{self.lookup}"
        return queryset.filter(**{lookup_expr: value})
