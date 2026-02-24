import logging

from core.admin_mixins import AdminIconDecorator, BaseAdmin
from django import forms
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from users.utils.helpers import user_is_verified_employee

from locations.forms import *
from locations.models import *
from locations.utils.location_filters import *

logger = logging.getLogger(__name__)

@AdminIconDecorator.register_with_icon(GlobalRegion)
class GlobalRegionAdmin(BaseAdmin):
    form = GlobalRegionForm
    list_display = ('name', 'countries_display', 'code', 'is_active')
    list_filter = (GlobalRegionNameFilter, IsActiveFilter)
    search_fields = ('name', 'asciiname', 'slug', 'code')
    date_hierarchy = 'created_at'
    list_per_page = 50
    prefetch_related_fields = ['countries']
    actions = ['soft_delete', 'restore']
    readonly_fields = ('geoname_id', 'created_by', 'updated_by', 'created_at', 'updated_at')

    base_fieldsets_config = [
        (None, {
            'fields': ('name', 'code', 'asciiname', 'slug', 'geoname_id')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        return tuple(sorted(set(readonly).union(self.readonly_fields)))

    def countries_display(self, obj):
        return format_html(
            ', '.join(
                f'<a href="{reverse("admin:locations_customcountry_change", args=[c.pk])}">{c.name}</a>'
                for c in obj.countries.filter(deleted_at__isnull=True)
            ) or 'None'
        )
    countries_display.short_description = "Countries"

    def get_list_filter(self, request):
        base_filters = [GlobalRegionNameFilter, IsActiveFilter]
        return base_filters

@AdminIconDecorator.register_with_icon(CustomCountry)
class CountryAdmin(BaseAdmin):
    form = CustomCountryForm
    list_display = ('name', 'country_code', 'currency_code', 'global_region_display', 'is_active')
    search_fields = ('name', 'country_code', 'currency_code', 'asciiname', 'slug')
    date_hierarchy = 'created_at'
    ordering = ('-id',)
    list_per_page = 50
    prefetch_related_fields = ['global_regions']
    autocomplete_fields = ['global_regions']
    actions = ['soft_delete', 'restore']
    readonly_fields = ('geoname_id', 'asciiname', 'slug', 'country_code', 'created_by', 'updated_by', 'created_at', 'updated_at')

    base_fieldsets_config = [
        (None, {
            'fields': ('name', 'country_code', 'currency_code', 'currency_symbol', 'currency_name', 'country_phone_code')
        }),
        (_('Details'), {
            'fields': ('postal_code_regex', 'country_languages', 'country_capital', 'population', 'global_regions', 'asciiname', 'slug', 'geoname_id', 'admin_codes')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        return tuple(sorted(set(readonly).union(self.readonly_fields)))

    def global_region_display(self, obj):
        return ', '.join(region.name for region in obj.global_regions.filter(deleted_at__isnull=True)) or 'None'
    global_region_display.short_description = 'Global Region'

    def get_list_filter(self, request):
        base_filters = [CountryCodeFilter, CurrencyCodeFilter, IsActiveFilter]

        if user_is_verified_employee(request):
            base_filters.insert(0, GlobalRegionFilter)     # privilege escalation = visual priority

        return base_filters


@AdminIconDecorator.register_with_icon(CustomRegion)
class RegionAdmin(BaseAdmin):
    form = CustomRegionForm
    list_display = ('name', 'country', 'code_display', 'is_active')
    list_display_links = ('id', 'name',)
    search_fields = ('name', 'code', 'country__name')
    list_per_page = 25
    date_hierarchy = 'created_at'
    ordering = ('-id',)
    select_related_fields = ['country']
    autocomplete_fields = ['country']
    actions = ['soft_delete', 'restore']
    readonly_fields = ('geoname_id', 'asciiname', 'slug', 'created_by', 'updated_by', 'created_at', 'updated_at')

    def get_list_display(self, request):
    # Always include code_display and is_active
        return ('id', 'name', 'country', 'code_display', 'is_active')

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('country')
        # Let list_filter handle filtering now
        return qs

    base_fieldsets_config = [
        (None, {'fields': ('name', 'country', 'code', 'asciiname', 'slug', 'geoname_id')}),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        return tuple(sorted(set(readonly).union(self.readonly_fields)))

    def id_display(self, obj):
        return obj.id if obj else '-'
    id_display.short_description = 'ID'

    def code_display(self, obj):
        return obj.code if obj else '-'
    code_display.short_description = 'Administrative Code'

    def get_list_filter(self, request):
        base_filters = [IsActiveFilter]

        if user_is_verified_employee(request):
            base_filters.insert(0, CountryFilter)

        return base_filters


@AdminIconDecorator.register_with_icon(CustomSubRegion)
class SubRegionAdmin(BaseAdmin):
    form = CustomSubRegionForm
    list_display = ('name', 'code', 'region', 'country_display', 'is_active')
    search_fields = ('name', 'region__name', 'region__country__name', 'asciiname', 'slug', 'code')
    date_hierarchy = 'created_at'
    ordering = ('-id',)
    list_per_page = 50
    select_related_fields = ['region__country']
    autocomplete_fields = ['region']
    actions = ['soft_delete', 'restore']
    readonly_fields = ('geoname_id', 'asciiname', 'slug', 'code', 'created_by', 'updated_by', 'created_at', 'updated_at')

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('region')
        return qs

    base_fieldsets_config = [
        (None, {
            'fields': ('name', 'code', 'asciiname', 'slug', 'geoname_id')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        return tuple(sorted(set(readonly).union(self.readonly_fields)))

    def country_display(self, obj):
        return obj.region.country.name if obj.region and obj.region.country else '-'
    country_display.short_description = 'Country'

    def get_list_filter(self, request):
        base_filters = [RegionFilter, IsActiveFilter]

        if user_is_verified_employee(request):
            base_filters.insert(0, CountryFilter)

        return base_filters


class LocationInlineForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ['street_address', 'postal_code', 'latitude', 'longitude']
        labels = {
            'street_address': 'Locality',
        }

    def clean(self):
        cleaned_data = super().clean()
        postal_code = cleaned_data.get('postal_code')
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        if postal_code and (latitude is None or longitude is None):
            raise forms.ValidationError("Latitude and longitude are required when postal code is provided.")
        return cleaned_data

class LocationInline(admin.TabularInline):
    model = Location
    form = LocationInlineForm
    extra = 1
    fields = ('street_address', 'postal_code', 'latitude', 'longitude')
    readonly_fields = ('created_by', 'updated_by', 'created_at', 'updated_at')
    can_delete = True
    show_change_link = True
    verbose_name = "Area"
    verbose_name_plural = "Areas"

    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            deleted_at__isnull=True,
            postal_code__isnull=False,
            latitude__isnull=False,
            longitude__isnull=False
        ).select_related('city')

@AdminIconDecorator.register_with_icon(CustomCity)
class CityAdmin(BaseAdmin):
    form = CustomCityForm
    list_display = ('location_name', 'country_display', 'region_states', 'subregion_districts', 'timezone_display', 'postal_code_display', 'latitude', 'longitude', 'is_active')
    search_fields = ('name', 'subregion__region__country__name', 'subregion__region__name', 'subregion__name', 'asciiname', 'slug', 'geoname_id')
    date_hierarchy = 'created_at'
    list_per_page = 50
    select_related_fields = ['subregion', 'subregion__region', 'subregion__region__country', 'timezone']
    autocomplete_fields = ['subregion', 'timezone']
    inlines = [LocationInline]
    actions = ['soft_delete', 'restore']
    readonly_fields = ('geoname_id', 'asciiname', 'slug', 'code', 'created_by', 'updated_by', 'created_at', 'updated_at')

    base_fieldsets_config = [
        (None, {
            'fields': ('name', 'country', 'region', 'subregion', 'timezone', 'latitude', 'longitude', 'code', 'asciiname', 'slug', 'geoname_id')
        }),
    ]

    def get_list_filter(self, request):
        base_filters = [RegionFilter, SubRegionFilter, TimezoneFilter, IsActiveFilter]

        if user_is_verified_employee(request):
            base_filters.insert(0, CountryFilter)

        return base_filters

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        return tuple(sorted(set(readonly).union(self.readonly_fields)))

    def country_display(self, obj):
        return obj.subregion.region.country.name if obj.subregion and obj.subregion.region and obj.subregion.region.country else '-'
    country_display.short_description = 'Country'

    def timezone_display(self, obj):
        return obj.timezone.display_name if obj.timezone else '-'
    timezone_display.short_description = 'Timezone'

    def region_states(self, obj):
        return obj.subregion.region.name if obj.subregion and obj.subregion.region else '-'
    region_states.short_description = 'Region/States'

    def subregion_districts(self, obj):
        if not obj.subregion:
            return '-'

        # ---- Subregion name -------------------------------------------------
        subregion = obj.subregion.name

        # ---- Districts -------------------------------------------------------
        # CustomCity belongs to CustomSubRegion (FK)
        # CustomSubRegion does **not** have a direct districts field.
        # In the Indian admin hierarchy:
        #   Country → Region (State) → SubRegion (District) → City
        #
        # So the “districts” you want to show are simply the **subregion name**
        # itself, because the SubRegion *is* the district.
        #
        # If you ever add a separate District model later, just change the line
        # marked with <<<--- EDIT HERE --->>>.

        districts = subregion                     # <<<--- EDIT HERE IF NEEDED --->>>
        # Example for a future ManyToMany:
        # districts_qs = obj.subregion.districts.all()
        # districts = format_html_join(', ', '{}', ((d.name,) for d in districts_qs))

        return format_html(
            '{sub}',
            sub=subregion,
            dist=districts,
        )

    subregion_districts.short_description = format_html(
        'Subregion<br><small>District</small>'
    )
    subregion_districts.admin_order_field = 'subregion__name'   # click to sort

    def postal_code_display(self, obj):
        country = obj.subregion.region.country if obj.subregion and obj.subregion.region and obj.subregion.region.country else None
        if country and not country.has_postal_code:
            return 'Postal Code not supported'
        postal_codes = obj.locations.filter(
            deleted_at__isnull=True,
            postal_code__isnull=False,
            latitude__isnull=False,
            longitude__isnull=False
        ).values_list('postal_code', flat=True)
        postal_codes = [pc for pc in postal_codes if pc]
        return ', '.join(postal_codes) if postal_codes else 'Data unavailable'
    postal_code_display.short_description = 'Postal Codes'

    def location_name(self, obj):
        return obj.name
    location_name.short_description = 'City Name'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.request = request
        return form

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        if request.method == 'POST' and request.POST.get('repopulate'):
            obj = self.get_object(request, object_id)
            form_class = self.get_form(request, obj)
            form = form_class(request.POST, instance=obj)
            if form.is_valid():
                new_data = form.cleaned_data
                country = new_data.get('country')
                region = new_data.get('region')
                country_id = country.id if country else ''
                region_id = region.id if region else ''
                if object_id:
                    base_url = reverse('admin:locations_customcity_change', args=[object_id])
                else:
                    base_url = reverse('admin:locations_customcity_add')
                url = f"{base_url}?country={country_id}&region={region_id}"
                return HttpResponseRedirect(url)
        return super().changeform_view(request, object_id, form_url, extra_context)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'subregion':
            if request.method == 'POST':
                region_id = request.POST.get('region')
            else:
                try:
                    city_id = request.resolver_match.kwargs.get('object_id')
                    if city_id:
                        city = CustomCity.objects.get(id=city_id)
                        region_id = city.subregion.region.id if city.subregion and city.subregion.region else None
                    else:
                        region_id = request.GET.get('region')
                except CustomCity.DoesNotExist:
                    region_id = None
            if region_id:
                kwargs['queryset'] = CustomSubRegion.objects.filter(
                    region_id=region_id,
                    deleted_at__isnull=True,
                    is_active=True
                ).order_by('name')
            else:
                kwargs['queryset'] = CustomSubRegion.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_urls(self):
        urls = super().get_urls()
        return urls

@AdminIconDecorator.register_with_icon(Timezone)
class TimezoneAdmin(BaseAdmin):
    form = TimezoneForm
    list_display = ('display_timezone', 'display_name', 'display_gmt_offset_jan', 'display_dst_offset_jul', 'country_code', 'is_active')
    search_fields = ('timezone_id', 'display_name', 'country_code')
    date_hierarchy = 'created_at'
    ordering = ('-id',)
    list_per_page = 50
    readonly_fields = ('created_by', 'updated_by', 'created_at', 'updated_at')

    base_fieldsets_config = [
        (None, {
            'fields': ('timezone_id', 'gmt_offset_jan', 'dst_offset_jul', 'display_name',  'raw_offset', 'country_code')
        }),
    ]
    def get_object(self, request, object_id, from_field=None):
        """
        Decode custom _2F encoding for natural PKs with '/'.
        Incoming object_id: 'Africa_2FAbidjan' → 'Africa/Abidjan'
        """
        if object_id:
            # Handle your custom _2F replacement (instead of/in addition to %2F)
            object_id = object_id.replace('_2F', '/')
            # Optional: Also handle standard %2F if mixed
            # from urllib.parse import unquote
            # object_id = unquote(object_id)
        return super().get_object(request, object_id, from_field=from_field)

    def get_list_filter(self, request):
        base_filters = [TimezoneFilter, GMTOffsetFilter, DSTOffsetFilter, IsActiveFilter]

        if user_is_verified_employee(request):
            base_filters.insert(0, CountryFilter)

        return base_filters

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_list_display(self, request):
        return ('id', 'display_timezone', 'display_name', 'display_gmt_offset_jan', 'display_dst_offset_jul', 'country_code', 'is_active')

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        return tuple(sorted(set(readonly).union(self.readonly_fields)))

    @admin.display(description='Timezone')
    def display_timezone(self, obj):
        return obj.timezone_id

    @admin.display(description='GMT Offset Jan')
    def display_gmt_offset_jan(self, obj):
        return obj.gmt_offset_jan

    @admin.display(description='DST Offset Jul')
    def display_dst_offset_jul(self, obj):
        return obj.dst_offset_jul

    @admin.display(description='Country Code')
    def country_code(self, obj):
        return obj.country_code
