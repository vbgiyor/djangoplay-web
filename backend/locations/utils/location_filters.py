"""
Custom Django admin filters for the locations app.
These filters are designed to handle hierarchical location data (GlobalRegion -> Country -> Region -> SubRegion -> City -> Location)
and common status filters like active/inactive (soft delete).

Usage in admin.py:
- Import: from .filters import *
- Assign to list_filter in ModelAdmin classes, e.g., list_filter = (IsActiveFilter, CountryFilter, RegionFilter)
- For conditional filters, override get_list_filter in ModelAdmin.

Filters are reusable across models via dynamic queryset methods.
"""

from django.contrib import admin
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

# from teamcentral.models import Address
from teamcentral.models import Address

from locations.models import CustomCity, CustomCountry, CustomRegion, CustomSubRegion, GlobalRegion, Timezone


class IsActiveFilter(admin.SimpleListFilter):

    """
    Filter for active/inactive status (handles soft deletes via deleted_at).
    Choices: All, Active, Inactive.
    """

    title = _('Status')
    parameter_name = 'is_active'

    def lookups(self, request, model_admin):
        return (
            ('all', _('All')),
            ('active', _('Active')),
            ('inactive', _('Inactive')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(deleted_at__isnull=True, is_active=True)
        if self.value() == 'inactive':
            return queryset.filter(Q(deleted_at__isnull=False) | Q(is_active=False))
        return queryset


# class GlobalRegionFilter(admin.SimpleListFilter):
#     """
#     Filter for GlobalRegion (used in CustomCountryAdmin).
#     Shows active global regions only.
#     """
#     title = _('Global Region')
#     parameter_name = 'global_region'

#     def lookups(self, request, model_admin):
#         return [(gr.id, gr.name) for gr in GlobalRegion.objects.filter(deleted_at__isnull=True, is_active=True).order_by('name')]

#     def queryset(self, request, queryset):
#         if self.value():
#             return queryset.filter(global_regions__id=self.value())
#         return queryset

class GlobalRegionFilter(admin.SimpleListFilter):

    """Used by CustomCountry (M2M) – can be reused on any model that adds the same M2M."""

    title = _('Global Region')
    parameter_name = 'global_region'

    def lookups(self, request, model_admin):
        return [
            (gr.id, gr.name)
            for gr in GlobalRegion.objects.filter(
                deleted_at__isnull=True, is_active=True
            ).order_by('name')
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(global_regions__id=self.value())
        return queryset

class GlobalRegionNameFilter(admin.SimpleListFilter):
    title = _('Global Region Name')
    parameter_name = 'name'

    def lookups(self, request, model_admin):
        regions = GlobalRegion.objects.filter(
            deleted_at__isnull=True,
            is_active=True
        ).order_by('name')
        return [(region.name, region.name) for region in regions]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(name__exact=self.value())
        return queryset

class CountryFilter(admin.SimpleListFilter):

    """
    Filter for CustomCountry (used in RegionAdmin, SubRegionAdmin, CityAdmin, LocationAdmin, TimezoneAdmin).
    - For direct FK (e.g., CustomRegion.country): filters by country_id.
    - For indirect (e.g., CustomSubRegion.region__country): filters by region__country_id.
    - For M2M (e.g., CustomCountry.global_regions): not applicable here.
    Shows active countries only.
    """

    title = _('Country')
    parameter_name = 'country'

    def lookups(self, request, model_admin):
        return [(c.id, c.name) for c in CustomCountry.objects.filter(deleted_at__isnull=True, is_active=True).order_by('name')]

    def queryset(self, request, queryset):
        if self.value():
            model = queryset.model
            if hasattr(model, 'country'):  # Direct FK: CustomRegion
                return queryset.filter(country_id=self.value())
            elif hasattr(model, 'region'):  # Indirect via region: CustomSubRegion
                return queryset.filter(region__country_id=self.value())
            elif hasattr(model, 'subregion'):  # Indirect via subregion->region->country: CustomCity
                return queryset.filter(subregion__region__country_id=self.value())
            elif hasattr(model, 'city'):  # Indirect via city->subregion->region->country: Location
                return queryset.filter(city__subregion__region__country_id=self.value())
            elif model == Timezone:  # For Timezone.country_code (exact match)
                return queryset.filter(country_code__exact=CustomCountry.objects.get(id=self.value()).country_code)
        return queryset

# class CountryFilter(admin.SimpleListFilter):
#     title = _('Country')
#     parameter_name = 'country'

#     # mapping of model_name → path to country
#     COUNTRY_PATHS = {
#         # Locations app
#         'CustomCountry': 'id',
#         'CustomRegion': 'country_id',
#         'CustomSubRegion': 'region__country_id',
#         'CustomCity': 'subregion__region__country_id',
#         'Location': 'city__subregion__region__country_id',

#         # Entities app
#         'Entity': 'default_address__city__subregion__region__country_id',

#         # Timezone special case
#         'Timezone': 'country_code',
#         'Address': 'country__name',
#     }

#     def lookups(self, request, model_admin):
#         qs = CustomCountry.objects.all().order_by("name")
#         return [(str(c.id), c.name) for c in qs]

#     def queryset(self, request, queryset):
#         val = self.value()
#         if not val:
#             return queryset

#         model_name = queryset.model.__name__
#         path = self.COUNTRY_PATHS.get(model_name)

#         if not path:
#             # model not mapped → do nothing silently
#             return queryset

#         # timezone special case (code instead of FK)
#         if model_name == "Timezone":
#             try:
#                 cc = CustomCountry.objects.get(id=val).country_code
#             except CustomCountry.DoesNotExist:
#                 return queryset
#             return queryset.filter(**{path: cc})

#         # Special case: Address (country is CharField, not FK)
#         if model_name == "Address":
#             try:
#                 country_name = CustomCountry.objects.get(id=val).name
#             except CustomCountry.DoesNotExist:
#                 return queryset
#             return queryset.filter(country=country_name)

#         # normal FK chain
#         return queryset.filter(**{path: val})

class RegionFilter(admin.SimpleListFilter):

    """
    Filter for CustomRegion (used in SubRegionAdmin, CityAdmin, LocationAdmin).
    - For direct FK (e.g., CustomSubRegion.region): filters by region_id.
    - For indirect (e.g., CustomCity.subregion__region): filters by subregion__region_id.
    Shows active regions only, dynamically scoped by country if provided in request.GET.
    """

    title = _('Region/State')
    parameter_name = 'region'

    def lookups(self, request, model_admin):
        regions = CustomRegion.objects.filter(deleted_at__isnull=True, is_active=True).order_by('name')
        # Scope to country if provided (e.g., via CountryFilter)
        country_id = request.GET.get('country')
        if country_id:
            regions = regions.filter(country_id=country_id)
        return [(r.id, r.name) for r in regions]

    def queryset(self, request, queryset):
        if self.value():
            model = queryset.model
            if hasattr(model, 'region'):  # Direct FK: CustomSubRegion
                return queryset.filter(region_id=self.value())
            elif hasattr(model, 'subregion'):  # Indirect via subregion: CustomCity
                return queryset.filter(subregion__region_id=self.value())
            elif hasattr(model, 'city'):  # Indirect via city->subregion->region: Location
                return queryset.filter(city__subregion__region_id=self.value())
        return queryset


class SubRegionFilter(admin.SimpleListFilter):

    """
    Filter for CustomSubRegion (used in CityAdmin, LocationAdmin).
    - For direct FK (e.g., CustomCity.subregion): filters by subregion_id.
    - For indirect (e.g., Location.city__subregion): filters by city__subregion_id.
    Shows active subregions only, dynamically scoped by region (and country) if provided.
    """

    title = _('Subregion/District')
    parameter_name = 'subregion'

    def lookups(self, request, model_admin):
        subregions = CustomSubRegion.objects.filter(deleted_at__isnull=True, is_active=True).order_by('name')
        # Scope to region if provided
        region_id = request.GET.get('region')
        if region_id:
            subregions = subregions.filter(region_id=region_id)
        # Further scope to country if no region but country provided
        elif request.GET.get('country'):
            country_id = request.GET.get('country')
            subregions = subregions.filter(region__country_id=country_id)
        return [(sr.id, sr.name) for sr in subregions]

    def queryset(self, request, queryset):
        if self.value():
            model = queryset.model
            if hasattr(model, 'subregion'):  # Direct FK: CustomCity
                return queryset.filter(subregion_id=self.value())
            elif hasattr(model, 'city'):  # Indirect via city: Location
                return queryset.filter(city__subregion_id=self.value())
        return queryset


class CityFilter(admin.SimpleListFilter):

    """
    Filter for CustomCity (used in LocationAdmin).
    Filters by city_id directly.
    Shows active cities only, dynamically scoped by subregion (and higher levels) if provided.
    """

    title = _('City')
    parameter_name = 'city'

    def lookups(self, request, model_admin):
        cities = CustomCity.objects.filter(deleted_at__isnull=True, is_active=True).order_by('name')
        # Scope to subregion if provided
        subregion_id = request.GET.get('subregion')
        if subregion_id:
            cities = cities.filter(subregion_id=subregion_id)
        # Further scope to region if no subregion but region provided
        elif request.GET.get('region'):
            region_id = request.GET.get('region')
            cities = cities.filter(subregion__region_id=region_id)
        # Further scope to country if no region/subregion but country provided
        elif request.GET.get('country'):
            country_id = request.GET.get('country')
            cities = cities.filter(subregion__region__country_id=country_id)
        return [(c.id, c.name) for c in cities]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(city_id=self.value())
        return queryset


class TimezoneFilter(admin.SimpleListFilter):

    """
    Filter for Timezone (used in CityAdmin).
    Filters by timezone_id directly.
    Shows active timezones only, optionally scoped by country if provided.
    """

    title = _('Timezone')
    parameter_name = 'timezone'

    def lookups(self, request, model_admin):
        timezones = Timezone.objects.filter(deleted_at__isnull=True, is_active=True).order_by('display_name')
        # Scope to country if provided
        country_id = request.GET.get('country')
        if country_id:
            country_code = CustomCountry.objects.get(id=country_id).country_code
            timezones = timezones.filter(country_code=country_code)
        return [(tz.timezone_id, tz.display_name) for tz in timezones]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(timezone_id=self.value())
        return queryset


# Additional utility filters for specific fields (e.g., codes, sources)
class LocationSourceFilter(admin.SimpleListFilter):

    """
    Filter for location_source (common across models: GlobalRegion, CustomCountry, etc.).
    Shows distinct active sources.
    """

    title = _('Location Source')
    parameter_name = 'location_source'

    def lookups(self, request, model_admin):
        model = model_admin.model
        sources = model.objects.filter(deleted_at__isnull=True, is_active=True).values_list('location_source', flat=True).distinct().exclude(location_source__isnull=True).exclude(location_source__exact='')
        return [(s, s) for s in sorted(sources)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(location_source__exact=self.value())
        return queryset


class CurrencyCodeFilter(admin.SimpleListFilter):

    """
    Filter for currency_code (specific to CustomCountryAdmin).
    Shows distinct active currency codes.
    """

    title = _('Currency Code')
    parameter_name = 'currency_code'

    def lookups(self, request, model_admin):
        currencies = CustomCountry.objects.filter(deleted_at__isnull=True, is_active=True).values_list('currency_code', flat=True).distinct().exclude(currency_code__isnull=True).exclude(currency_code__exact='')
        return [(c, c) for c in sorted(currencies)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(currency_code__exact=self.value())
        return queryset


class CountryCodeFilter(admin.SimpleListFilter):

    """
    Filter for country_code (used in TimezoneAdmin for country_code field).
    Shows active countries' codes.
    """

    title = _('Country Code')
    parameter_name = 'country_code'

    def lookups(self, request, model_admin):
        return [(c.country_code, c.country_code) for c in CustomCountry.objects.filter(deleted_at__isnull=True, is_active=True).exclude(country_code__isnull=True).order_by('country_code')]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(country_code__exact=self.value())
        return queryset

class GMTOffsetFilter(admin.SimpleListFilter):

    """
    Filter for GMT Offset (January) in TimezoneAdmin.
    Allows filtering by distinct gmt_offset_jan values.
    """

    title = _('GMT Offset (Jan)')
    parameter_name = 'gmt_offset_jan'

    def lookups(self, request, model_admin):
        offsets = (
            model_admin.model.objects
            .filter(deleted_at__isnull=True)
            .values_list('gmt_offset_jan', flat=True)
            .distinct()
            .order_by('gmt_offset_jan')
        )
        return [(str(o), f"{o:+.2f}") for o in offsets]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(gmt_offset_jan=self.value())
        return queryset


class GMTOffsetFilter(admin.SimpleListFilter):

    """
    Filter for GMT Offset (January) in TimezoneAdmin.
    Allows filtering by distinct gmt_offset_jan values.
    """

    title = _('GMT Offset (Jan)')
    parameter_name = 'gmt_offset_jan'

    def lookups(self, request, model_admin):
        offsets = (
            model_admin.model.objects
            .filter(deleted_at__isnull=True)
            .values_list('gmt_offset_jan', flat=True)
            .distinct()
            .order_by('gmt_offset_jan')
        )
        return [(str(o), f"{o:+.2f}") for o in offsets]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(gmt_offset_jan=self.value())
        return queryset


class DSTOffsetFilter(admin.SimpleListFilter):

    """
    Filter for DST Offset (July) in TimezoneAdmin.
    Allows filtering by distinct dst_offset_jul values.
    """

    title = _('DST Offset (Jul)')
    parameter_name = 'dst_offset_jul'

    def lookups(self, request, model_admin):
        offsets = (
            model_admin.model.objects
            .filter(deleted_at__isnull=True)
            .values_list('dst_offset_jul', flat=True)
            .distinct()
            .order_by('dst_offset_jul')
        )
        return [(str(o), f"{o:+.2f}") for o in offsets]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(dst_offset_jul=self.value())
        return queryset


class AddressTypeFilter(admin.SimpleListFilter):
    title = _('Address Type')
    parameter_name = 'addr_type'

    def lookups(self, request, model_admin):
        addr_type = (Address.objects
                     .exclude(address_type__exact='')
                     .values_list('address_type', flat=True)
                     .distinct()
                     .order_by('address_type'))
        return [(c, c) for c in addr_type if c]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(address_type__iexact=self.value())
        return queryset

class AddressCountryFilter(admin.SimpleListFilter):
    title = _('Country')
    parameter_name = 'addr_country'

    def lookups(self, request, model_admin):
        countries = (Address.objects
                     .exclude(country__exact='')
                     .values_list('country', flat=True)
                     .distinct()
                     .order_by('country'))
        return [(c, c) for c in countries if c]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(country__iexact=self.value())
        return queryset


class AddressStateFilter(admin.SimpleListFilter):
    title = _('State')
    parameter_name = 'addr_state'

    def lookups(self, request, model_admin):
        qs = Address.objects.exclude(state__exact='')

        # Auto-scope by selected country
        country = request.GET.get('addr_country')
        if country:
            qs = qs.filter(country__iexact=country)

        states = (qs.values_list('state', flat=True)
                  .distinct()
                  .order_by('state'))
        return [(s, s) for s in states if s]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(state__iexact=self.value())
        return queryset


class AddressCityFilter(admin.SimpleListFilter):
    title = _('City')
    parameter_name = 'addr_city'

    def lookups(self, request, model_admin):
        qs = Address.objects.exclude(city__exact='')

        # Auto-scope by country + state
        country = request.GET.get('addr_country')
        state = request.GET.get('addr_state')

        if country:
            qs = qs.filter(country__iexact=country)
        if state:
            qs = qs.filter(state__iexact=state)

        cities = (qs.values_list('city', flat=True)
                  .distinct()
                  .order_by('city'))
        return [(c, c) for c in cities if c]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(city__iexact=self.value())
        return queryset


class DepartmentCodeFilter(admin.SimpleListFilter):
    title = _('Code')
    parameter_name = 'dept_code'

    def lookups(self, request, model_admin):
        # from teamcentral.models import Department
        from teamcentral.models import Department
        qs = Department.objects.exclude(code__exact='')

        # Auto-scope by country + state
        code = request.GET.get('dept_code')

        if code:
            qs = qs.filter(code__iexact=code)

        codes = (qs.values_list('code', flat=True)
                  .distinct()
                  .order_by('code'))
        return [(c, c) for c in codes if c]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(code__iexact=self.value())
        return queryset


# Export all filters for easy import
__all__ = [
    'IsActiveFilter',
    'GlobalRegionFilter',
    'GlobalRegionNameFilter',
    'CountryFilter',
    'RegionFilter',
    'SubRegionFilter',
    'CityFilter',
    'TimezoneFilter',
    'GMTOffsetFilter',
    'DSTOffsetFilter',
    'LocationSourceFilter',
    'CurrencyCodeFilter',
    'CountryCodeFilter',
    'AddressTypeFilter',
    'AddressCountryFilter',
    'AddressStateFilter',
    'AddressCityFilter',
    'DepartmentCodeFilter',
]
