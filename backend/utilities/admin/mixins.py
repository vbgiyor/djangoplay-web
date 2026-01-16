import json
import logging

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django_redis import get_redis_connection
from locations.models import CustomCountry

logger = logging.getLogger(__name__)

class CountryFilterMixin:

    """Mixin to add country-based filtering to Django admin."""

    # Default model field mapping for country fields
    country_field_mapping = {
        'Invoice': 'billing_country',
        'LineItem': 'invoice__billing_country',
        'Address': 'country',
        'TaxProfile': 'country',
        'Contact': 'country',
        'CustomCity': 'subregion__region__country',  # Add CustomCity with the correct field path
        'CustomRegion': 'country',  # For CustomRegionAdmin
        'CustomSubRegion': 'region__country',  # For CustomSubRegionAdmin
        'Location': 'city__subregion__region__country',
        'Employee': 'country',
        'Member': 'country'
    }

    class CountryAdminFilter(admin.SimpleListFilter):
        title = _('Country')
        parameter_name = 'country_filter'

        def __init__(self, request, params, model, model_admin):
            super().__init__(request, params, model, model_admin)
            self.model_name = model.__name__
            self.country_field = model_admin.country_field_mapping.get(self.model_name)
            if not self.country_field:
                raise ValidationError(f"CountryFilter does not support model: {self.model_name}")

        def lookups(self, request, model_admin):
            redis_conn = get_redis_connection('default')
            cache_key = 'locations:country:lookup'
            cached_countries = redis_conn.get(cache_key)
            if cached_countries:
                choices = json.loads(cached_countries)
                logger.debug(f"Cached country choices: {choices}")
                return choices
            countries = CustomCountry.objects.filter(is_active=True).values('country_code', 'name')
            choices = [(c['country_code'], c['name']) for c in countries]
            logger.debug(f"Fresh country choices: {choices}")
            redis_conn.setex(cache_key, 3600, json.dumps(choices))
            return choices

        def queryset(self, request, queryset):
            """Apply country-based filtering to the queryset."""
            logger.debug(f"Request GET parameters: {request.GET}")
            country_code = self.value()
            if not country_code:
                return queryset

            logger.debug(f"Applying CountryAdminFilter: model={self.model_name}, country_code={country_code}")

            # Apply is_active filter based on model
            if self.model_name == 'LineItem':
                queryset = queryset.filter(invoice__is_active=True)
            else:
                # Ensure the related country is active
                queryset = queryset.filter(**{f"{self.country_field}__is_active": True})

            # Filter by country code
            queryset = queryset.filter(**{f"{self.country_field}__country_code__iexact": country_code})
            logger.info(f"Filtered {self.model_name} queryset: {queryset.count()} records")
            return queryset

    # Add the filter to list_filter
    list_filter = (CountryAdminFilter,)
