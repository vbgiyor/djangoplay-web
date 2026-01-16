import logging

from dal import autocomplete
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from utilities.api.rate_limits import CustomSearchThrottle

from locations.exceptions import InvalidLocationData
from locations.models import (
    CustomCity,
    CustomCountry,
    CustomRegion,
    CustomSubRegion,
    GlobalRegion,
    Timezone,
)

logger = logging.getLogger(__name__)


class BaseAutocompleteView(autocomplete.Select2QuerySetView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [CustomSearchThrottle]
    error_class = InvalidLocationData

    def get_queryset(self):
        return self.model.objects.filter(
            deleted_at__isnull=True,
            is_active=True,
        )


class GlobalRegionAutocomplete(BaseAutocompleteView):
    model = GlobalRegion

    def get_queryset(self):
        qs = super().get_queryset()
        if self.q:
            qs = qs.filter(Q(name__trigram_similar=self.q) | Q(code__trigram_similar=self.q))
        return qs.order_by("name")


class CustomCountryAutocomplete(BaseAutocompleteView):
    model = CustomCountry

    def get_queryset(self):
        qs = super().get_queryset()
        if self.q:
            qs = qs.filter(
                Q(name__trigram_similar=self.q)
                | Q(asciiname__trigram_similar=self.q)
                | Q(country_code__iexact=self.q)
            )
        return qs.order_by("name")


class CustomRegionAutocomplete(BaseAutocompleteView):
    model = CustomRegion

    def get_queryset(self):
        qs = super().get_queryset()
        country_id = self.forwarded.get("country")
        if country_id:
            qs = qs.filter(country_id=country_id)
        if self.q:
            qs = qs.filter(name__trigram_similar=self.q)
        return qs.order_by("name")


class CustomSubRegionAutocomplete(BaseAutocompleteView):
    model = CustomSubRegion

    def get_queryset(self):
        qs = super().get_queryset()
        region_id = self.forwarded.get("region")
        if region_id:
            qs = qs.filter(region_id=region_id)
        if self.q:
            qs = qs.filter(name__trigram_similar=self.q)
        return qs.order_by("name")


class CityAutocomplete(BaseAutocompleteView):
    model = CustomCity

    def get_queryset(self):
        qs = super().get_queryset()
        subregion_id = self.forwarded.get("subregion")
        if subregion_id:
            qs = qs.filter(subregion_id=subregion_id)
        if self.q:
            qs = qs.filter(name__trigram_similar=self.q)
        return qs.order_by("name")


class TimezoneAutocomplete(BaseAutocompleteView):
    model = Timezone

    def get_queryset(self):
        qs = super().get_queryset()
        if self.q:
            qs = qs.filter(
                Q(display_name__trigram_similar=self.q)
                | Q(timezone_id__trigram_similar=self.q)
            )
        return qs.order_by("display_name")
