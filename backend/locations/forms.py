# forms.py (updated)
import logging

import redis
from core.utils.redis_client import redis_client
from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from utilities.utils.general.normalize_text import normalize_text

from locations.exceptions import InvalidLocationData
from locations.models import CustomCity, CustomCountry, CustomRegion, CustomSubRegion, GlobalRegion, Location, Timezone

logger = logging.getLogger(__name__)

class GlobalRegionForm(forms.ModelForm):

    """Form for creating and updating GlobalRegion instances."""

    class Meta:
        model = GlobalRegion
        fields = ['name', 'code', 'asciiname', 'slug', 'geoname_id', 'location_source']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 100,
                'placeholder': 'Enter global region name',
            }),
            'code': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 10,
                'placeholder': 'Enter global region code',
            }),
            'asciiname': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 100,
                'placeholder': 'Enter ASCII name (optional)',
            }),
            'slug': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 100,
                'placeholder': 'Enter slug (auto-generated if blank)',
            }),
            'geoname_id': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'placeholder': 'Enter Geoname ID (optional)',
            }),
            'location_source': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 50,
                'placeholder': 'Enter location source (e.g., geonames, GOI)',
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = normalize_text(name)
            if len(name) > 100:
                raise InvalidLocationData(
                    message="Global region name cannot exceed 100 characters.",
                    code="invalid_name",
                    details={"field": "name", "value": name}
                )
        return name

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            code = normalize_text(code)
            if len(code) > 10:
                raise InvalidLocationData(
                    message="Global region code cannot exceed 10 characters.",
                    code="invalid_code",
                    details={"field": "code", "value": code}
                )
        return code

    def clean_asciiname(self):
        asciiname = self.cleaned_data.get('asciiname')
        if asciiname:
            asciiname = normalize_text(asciiname)
            if len(asciiname) > 100:
                raise InvalidLocationData(
                    message="ASCII name cannot exceed 100 characters.",
                    code="invalid_asciiname",
                    details={"field": "asciiname", "value": asciiname}
                )
        return asciiname

    def clean_location_source(self):
        location_source = self.cleaned_data.get('location_source')
        if location_source:
            location_source = normalize_text(location_source)
            if len(location_source) > 50:
                raise InvalidLocationData(
                    message="Location source cannot exceed 50 characters.",
                    code="invalid_location_source",
                    details={"field": "location_source", "value": location_source}
                )
        return location_source

    @transaction.atomic
    def save(self, commit=True, user=None):
        logger.debug(f"Saving GlobalRegionForm: {self.cleaned_data.get('name', 'New Global Region')}, user={user}")
        instance = super().save(commit=False)
        cache_key = f"global_region:{instance.id or 'new'}"
        try:
            redis_client.delete(cache_key)
            logger.debug(f"Invalidated cache for GlobalRegion: {cache_key}")
        except redis.RedisError as e:
            logger.warning(f"Failed to invalidate cache for {cache_key}: {str(e)}")

        if user:
            if not instance.pk:
                instance.created_by = user
            instance.updated_by = user
        if commit:
            instance.save(user=user, skip_validation=False)
            logger.info(f"Saved GlobalRegion: {instance.name} (ID: {instance.id})")
        return instance

class CustomCountryForm(forms.ModelForm):

    """Form for creating and updating CustomCountry instances."""

    class Meta:
        model = CustomCountry
        fields = [
            'name', 'country_code', 'asciiname', 'alternatenames', 'slug', 'geoname_id',
            'country_capital', 'currency_symbol', 'currency_code', 'currency_name',
            'country_phone_code', 'postal_code_regex', 'country_languages', 'population',
            'has_postal_code', 'postal_code_length', 'phone_number_length', 'admin_codes',
            'global_regions', 'location_source'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 100,
                'placeholder': 'Enter country name',
            }),
            'country_code': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 3,
                'placeholder': 'Enter country code (e.g., IN)',
            }),
            'asciiname': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 100,
                'placeholder': 'Enter ASCII name (optional)',
            }),
            'alternatenames': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'placeholder': 'Enter alternate names (comma-separated, optional)',
            }),
            'slug': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 100,
                'placeholder': 'Enter slug (auto-generated if blank)',
            }),
            'geoname_id': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'placeholder': 'Enter Geoname ID (optional)',
            }),
            'country_capital': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 100,
                'placeholder': 'Enter capital city',
            }),
            'currency_symbol': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 10,
                'placeholder': 'Enter currency symbol (e.g., ₹)',
            }),
            'currency_code': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 3,
                'placeholder': 'Enter currency code (e.g., INR)',
            }),
            'currency_name': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 100,
                'placeholder': 'Enter currency name (e.g., Indian Rupee)',
            }),
            'country_phone_code': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 10,
                'placeholder': 'Enter phone code (e.g., +91)',
            }),
            'postal_code_regex': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 100,
                'placeholder': 'Enter postal code regex (optional)',
            }),
            'country_languages': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 100,
                'placeholder': 'Enter languages (comma-separated, e.g., en-IN, hi-IN)',
            }),
            'population': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'min': 0,
                'placeholder': 'Enter population (optional)',
            }),
            'has_postal_code': forms.CheckboxInput(attrs={
                'class': 'p-2 rounded-md focus:ring focus:ring-blue-300',
            }),
            'postal_code_length': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'min': 0,
                'placeholder': 'Enter postal code length (optional)',
            }),
            'phone_number_length': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'min': 0,
                'placeholder': 'Enter phone number length (optional)',
            }),
            'admin_codes': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'placeholder': 'Enter admin codes (comma-separated, optional)',
            }),
            'global_regions': forms.SelectMultiple(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
            }),
            'location_source': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 50,
                'placeholder': 'Enter location source (e.g., geonames, GOI)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'global_regions' in self.fields:
            self.fields['global_regions'].queryset = GlobalRegion.objects.filter(is_active=True).only('id', 'name')
        else:
            logger.error("Field 'global_regions' not found in CustomCountryForm fields")

    def clean_country_code(self):
        country_code = self.cleaned_data.get('country_code')
        if country_code:
            country_code = normalize_text(country_code)
            if len(country_code) > 3:
                raise InvalidLocationData(
                    message="Country code cannot exceed 3 characters.",
                    code="invalid_country_code",
                    details={"field": "country_code", "value": country_code}
                )
        return country_code

    def clean_currency_code(self):
        currency_code = self.cleaned_data.get('currency_code')
        if currency_code:
            currency_code = normalize_text(currency_code)
            if len(currency_code) > 3:
                raise InvalidLocationData(
                    message="Currency code cannot exceed 3 characters.",
                    code="invalid_currency_code",
                    details={"field": "currency_code", "value": currency_code}
                )
        return currency_code

    @transaction.atomic
    def save(self, commit=True, user=None):
        logger.debug(f"Saving CustomCountryForm: {self.cleaned_data.get('name', 'New Country')}, user={user}")
        instance = super().save(commit=False)
        cache_key = f"country:{instance.id or 'new'}"
        try:
            redis_client.delete(cache_key)
            logger.debug(f"Invalidated cache for CustomCountry: {cache_key}")
        except redis.RedisError as e:
            logger.warning(f"Failed to invalidate cache for {cache_key}: {str(e)}")

        if user:
            if not instance.pk:
                instance.created_by = user
            instance.updated_by = user
        if commit:
            instance.save(user=user, skip_validation=False)
            logger.info(f"Saved CustomCountry: {instance.name} (ID: {instance.id})")
        return instance

class CustomRegionForm(forms.ModelForm):

    """Form for creating and updating CustomRegion instances."""

    country = forms.ModelChoiceField(
        queryset=CustomCountry.objects.filter(deleted_at__isnull=True, is_active=True),
        required=True,
        widget=forms.Select(attrs={'class': 'select2'}),
    )

    class Meta:
        model = CustomRegion
        fields = ['name', 'country', 'code', 'asciiname', 'slug', 'geoname_id', 'location_source']


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'country' in self.fields:
            self.fields['country'].queryset = CustomCountry.objects.filter(
                deleted_at__isnull=True, is_active=True
            ).only('id', 'name')
            logger.debug(f"CustomRegionForm initialized: country queryset count: {self.fields['country'].queryset.count()}")
        else:
            logger.error("Field 'country' not found in CustomRegionForm fields")

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = normalize_text(name)
            if len(name) > 200:
                raise InvalidLocationData(
                    message="Region name cannot exceed 200 characters.",
                    code="invalid_name",
                    details={"field": "name", "value": name}
                )
        return name

    @transaction.atomic
    def save(self, commit=True, user=None):
        logger.debug(f"Saving CustomRegionForm: {self.cleaned_data.get('name', 'New Region')}, user={user}")
        instance = super().save(commit=False)
        cache_key = f"region:{instance.id or 'new'}"
        try:
            redis_client.delete(cache_key)
            logger.debug(f"Invalidated cache for CustomRegion: {cache_key}")
        except redis.RedisError as e:
            logger.warning(f"Failed to invalidate cache for {cache_key}: {str(e)}")

        if user:
            if not instance.pk:
                instance.created_by = user
            instance.updated_by = user
        if commit:
            instance.save(user=user, skip_validation=False)
            logger.info(f"Saved CustomRegion: {instance.name} (ID: {instance.id})")
        return instance

class CustomSubRegionForm(forms.ModelForm):

    """Form for creating and updating CustomSubRegion instances."""

    region = forms.ModelChoiceField(
        queryset=CustomRegion.objects.filter(deleted_at__isnull=True, is_active=True),
        required=True,
        widget=forms.Select(attrs={'class': 'select2'}),
    )

    class Meta:
        model = CustomSubRegion
        fields = ['name', 'region', 'code', 'asciiname', 'slug', 'geoname_id', 'location_source']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 200,
                'placeholder': 'Enter subregion name',
            }),
            'region': forms.Select(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
            }),
            'code': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 20,
                'placeholder': 'Enter subregion code (optional)',
            }),
            'asciiname': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 100,
                'placeholder': 'Enter ASCII name (optional)',
            }),
            'slug': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 200,
                'placeholder': 'Enter slug (auto-generated if blank)',
            }),
            'geoname_id': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'placeholder': 'Enter Geoname ID (optional)',
            }),
            'location_source': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 50,
                'placeholder': 'Enter location source (e.g., geonames, GOI)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'region' in self.fields:
            self.fields['region'].queryset = CustomRegion.objects.filter(
                deleted_at__isnull=True, is_active=True
            ).only('id', 'name')
            logger.debug(f"CustomSubRegionForm initialized: region queryset count: {self.fields['region'].queryset.count()}")
        else:
            logger.error("Field 'region' not found in CustomSubRegionForm fields")

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = normalize_text(name)
            if len(name) > 200:
                raise InvalidLocationData(
                    message="Subregion name cannot exceed 200 characters.",
                    code="invalid_name",
                    details={"field": "name", "value": name}
                )
        return name

    @transaction.atomic
    def save(self, commit=True, user=None):
        logger.debug(f"Saving CustomSubRegionForm: {self.cleaned_data.get('name', 'New SubRegion')}, user={user}")
        instance = super().save(commit=False)
        cache_key = f"subregion:{instance.id or 'new'}"
        try:
            redis_client.delete(cache_key)
            logger.debug(f"Invalidated cache for CustomSubRegion: {cache_key}")
        except redis.RedisError as e:
            logger.warning(f"Failed to invalidate cache for {cache_key}: {str(e)}")

        if user:
            if not instance.pk:
                instance.created_by = user
            instance.updated_by = user
        if commit:
            instance.save(user=user, skip_validation=False)
            logger.info(f"Saved CustomSubRegion: {instance.name} (ID: {instance.id})")
        return instance

class CustomCityForm(forms.ModelForm):
    country = forms.ModelChoiceField(
        queryset=CustomCountry.objects.filter(deleted_at__isnull=True, is_active=True),
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300 select2',
            'data-autocomplete-url': '/console/locations/customcountry/autocomplete/',
        }),
    )
    region = forms.ModelChoiceField(
        queryset=CustomRegion.objects.filter(deleted_at__isnull=True, is_active=True),
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300 select2',
            'data-autocomplete-url': '/console/locations/customregion/autocomplete/',
        }),
        help_text="Select the region (must match the subregion's region)."
    )
    subregion = forms.ModelChoiceField(
        queryset=CustomSubRegion.objects.filter(deleted_at__isnull=True, is_active=True),
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300 select2',
            'data-autocomplete-url': '/console/locations/customsubregion/autocomplete/',
        }),
    )
    timezone = forms.ModelChoiceField(
        queryset=Timezone.objects.filter(deleted_at__isnull=True, is_active=True),
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300 select2',
            'data-autocomplete-url': '/console/locations/timezone/autocomplete/',
        }),
    )

    class Meta:
        model = CustomCity
        fields = ['name', 'country', 'region', 'subregion', 'code', 'asciiname', 'slug', 'geoname_id', 'latitude', 'longitude', 'timezone', 'location_source']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 200,
                'placeholder': 'Enter city name',
            }),
            'subregion': forms.Select(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'data-autocomplete-url': '/console/locations/customsubregion/autocomplete/',
            }),
            'code': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 20,
                'placeholder': 'Enter city code (optional)',
            }),
            'asciiname': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 100,
                'placeholder': 'Enter ASCII name (optional)',
            }),
            'slug': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 200,
                'placeholder': 'Enter slug (auto-generated if blank)',
            }),
            'geoname_id': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'placeholder': 'Enter Geoname ID (optional)',
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.000001',
                'placeholder': 'Enter latitude (optional)',
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.000001',
                'placeholder': 'Enter longitude (optional)',
            }),
            'timezone': forms.Select(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'data-autocomplete-url': '/console/locations/timezone/autocomplete/',
            }),
            'location_source': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 50,
                'placeholder': 'Enter location source (e.g., geonames, GOI)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize querysets for country, region, and subregion
        self.fields['country'].queryset = CustomCountry.objects.filter(deleted_at__isnull=True, is_active=True).order_by('name')
        self.fields['region'].queryset = CustomRegion.objects.filter(deleted_at__isnull=True, is_active=True).order_by('name')
        self.fields['subregion'].queryset = CustomSubRegion.objects.filter(deleted_at__isnull=True, is_active=True).order_by('name')

        country_id = None
        region_id = None
        if self.data:  # Handle POST data
            country_id = self.data.get('country')
            region_id = self.data.get('region')
        else:
            if self.instance and self.instance.pk:  # Handle existing instance
                if self.instance.subregion:
                    if self.instance.subregion.region:
                        self.initial['region'] = self.instance.subregion.region
                        region_id = self.instance.subregion.region.pk
                        if self.instance.subregion.region.country:
                            self.initial['country'] = self.instance.subregion.region.country
                            country_id = self.instance.subregion.region.country.pk
                    self.initial['subregion'] = self.instance.subregion
            if hasattr(self, 'request') and self.request:  # Handle GET parameters
                country_id = self.request.GET.get('country') or country_id
                region_id = self.request.GET.get('region') or region_id

        # Update region queryset based on country selection
        if country_id:
            try:
                country_id = int(country_id)
                self.fields['region'].queryset = CustomRegion.objects.filter(
                    country__id=country_id, deleted_at__isnull=True, is_active=True
                ).order_by('name')
                if 'country' not in self.initial:
                    self.initial['country'] = country_id
            except (ValueError, TypeError):
                self.fields['region'].queryset = CustomRegion.objects.filter(deleted_at__isnull=True, is_active=True).order_by('name')

        # Update subregion queryset based on region selection
        if region_id:
            try:
                region_id = int(region_id)
                self.fields['subregion'].queryset = CustomSubRegion.objects.filter(
                    region__id=region_id, deleted_at__isnull=True, is_active=True
                ).order_by('name')
                if 'region' not in self.initial:
                    self.initial['region'] = region_id
            except (ValueError, TypeError):
                self.fields['subregion'].queryset = CustomSubRegion.objects.filter(deleted_at__isnull=True, is_active=True).order_by('name')

        # Ensure fields are not disabled
        self.fields['region'].widget.attrs.pop('disabled', None)
        self.fields['subregion'].widget.attrs.pop('disabled', None)

        if 'timezone' in self.fields:
            self.fields['timezone'].queryset = Timezone.objects.filter(
                deleted_at__isnull=True, is_active=True
            ).order_by('display_name')
            logger.debug(f"CustomCityForm initialized: timezone queryset count: {self.fields['timezone'].queryset.count()}")
        else:
            logger.error("Field 'timezone' not found in CustomCityForm fields")

        # Ensure fields are not disabled
        self.fields['region'].widget.attrs.pop('disabled', None)
        self.fields['subregion'].widget.attrs.pop('disabled', None)

    def clean(self):
        cleaned_data = super().clean()
        country = cleaned_data.get('country')
        region = cleaned_data.get('region')
        subregion = cleaned_data.get('subregion')
        if country and region and region.country != country:
            raise forms.ValidationError(
                "The selected region must belong to the selected country."
            )
        if region and subregion and subregion.region != region:
            raise forms.ValidationError(
                "The selected subregion must belong to the selected region."
            )
        return cleaned_data

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = normalize_text(name)
            if len(name) > 200:
                raise InvalidLocationData(
                    message="City name cannot exceed 200 characters.",
                    code="invalid_name",
                    details={"field": "name", "value": name}
                )
        return name

    def clean_latitude(self):
        latitude = self.cleaned_data.get('latitude')
        if latitude is not None and (latitude < -90 or latitude > 90):
            raise InvalidLocationData(
                message="Latitude must be between -90 and 90.",
                code="invalid_latitude",
                details={"field": "latitude", "value": latitude}
            )
        return latitude

    def clean_longitude(self):
        longitude = self.cleaned_data.get('longitude')
        if longitude is not None and (longitude < -180 or longitude > 180):
            raise InvalidLocationData(
                message="Longitude must be between -180 and 180.",
                code="invalid_longitude",
                details={"field": "longitude", "value": longitude}
            )
        return longitude

    @transaction.atomic
    def save(self, commit=True, user=None):
        logger.debug(f"Saving CustomCityForm: {self.cleaned_data.get('name', 'New City')}, user={user}")
        instance = super().save(commit=False)
        cache_key = f"city:{instance.id or 'new'}"
        try:
            redis_client.delete(cache_key)
            logger.debug(f"Invalidated cache for CustomCity: {cache_key}")
        except redis.RedisError as e:
            logger.warning(f"Failed to invalidate cache for {cache_key}: {str(e)}")

        if user:
            if not instance.pk:
                instance.created_by = user
            instance.updated_by = user
        if commit:
            instance.save(user=user, skip_validation=False)
            logger.info(f"Saved CustomCity: {instance.name} (ID: {instance.id})")
        return instance

class LocationForm(forms.ModelForm):

    """Form for creating and updating Location instances."""

    class Meta:
        model = Location
        fields = ['city', 'postal_code', 'street_address', 'code', 'latitude', 'longitude', 'location_source']
        widgets = {
            'city': forms.Select(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 20,
                'placeholder': 'Enter postal code',
            }),
            'street_address': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 255,
                'placeholder': 'Enter street address',
            }),
            'code': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 20,
                'placeholder': 'Enter location code (optional)',
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.000001',
                'placeholder': 'Enter latitude (optional)',
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.000001',
                'placeholder': 'Enter longitude (optional)',
            }),
            'location_source': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 50,
                'placeholder': 'Enter location source (e.g., geonames, GOI)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['city'].queryset = self.fields['city'].queryset.filter(is_active=True).only('id', 'name')

    def clean_postal_code(self):
        postal_code = self.cleaned_data.get('postal_code')
        if postal_code:
            postal_code = normalize_text(postal_code)
            if len(postal_code) > 20:
                raise InvalidLocationData(
                    message="Postal code cannot exceed 20 characters.",
                    code="invalid_postal_code",
                    details={"field": "postal_code", "value": postal_code}
                )
        return postal_code

    def clean_latitude(self):
        latitude = self.cleaned_data.get('latitude')
        if latitude is not None and (latitude < -90 or latitude > 90):
            raise InvalidLocationData(
                message="Latitude must be between -90 and 90.",
                code="invalid_latitude",
                details={"field": "latitude", "value": latitude}
            )
        return latitude

    def clean_longitude(self):
        longitude = self.cleaned_data.get('longitude')
        if longitude is not None and (longitude < -180 or longitude > 180):
            raise InvalidLocationData(
                message="Longitude must be between -180 and 180.",
                code="invalid_longitude",
                details={"field": "longitude", "value": longitude}
            )
        return longitude

    @transaction.atomic
    def save(self, commit=True, user=None):
        logger.debug(f"Saving LocationForm: {self.cleaned_data.get('street_address', 'New Location')}, user={user}")
        instance = super().save(commit=False)
        cache_key = f"location:{instance.id or 'new'}"
        try:
            redis_client.delete(cache_key)
            logger.debug(f"Invalidated cache for Location: {cache_key}")
        except redis.RedisError as e:
            logger.warning(f"Failed to invalidate cache for {cache_key}: {str(e)}")

        if user:
            if not instance.pk:
                instance.created_by = user
            instance.updated_by = user
        if commit:
            instance.save(user=user, skip_validation=False)
            logger.info(f"Saved Location: {instance.street_address} (ID: {instance.id})")
        return instance


class TimezoneForm(forms.ModelForm):

    """Form for creating and updating Timezone instances."""

    class Meta:
        model = Timezone
        fields = ['timezone_id', 'display_name', 'country_code', 'gmt_offset_jan', 'dst_offset_jul', 'raw_offset']
        widgets = {
            'timezone_id': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 100,
                'placeholder': 'Enter timezone ID (e.g., Asia/Kolkata)',
            }),
            'display_name': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 100,
                'placeholder': 'Enter display name (e.g., India Standard Time)',
            }),
            'country_code': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': 3,
                'placeholder': 'Enter country code (e.g., IN)',
            }),
            'gmt_offset_jan': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'placeholder': 'Enter GMT offset for January',
            }),
            'dst_offset_jul': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'placeholder': 'Enter DST offset for July',
            }),
            'raw_offset': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'placeholder': 'Enter raw offset',
            }),
        }

    def clean_timezone_id(self):
        timezone_id = self.cleaned_data.get('timezone_id')
        if timezone_id:
            timezone_id = normalize_text(timezone_id)
            if len(timezone_id) > 100:
                raise ValidationError("Timezone ID cannot exceed 100 characters.")
        return timezone_id

    def clean_country_code(self):
        country_code = self.cleaned_data.get('country_code')
        if country_code:
            country_code = normalize_text(country_code)
            if len(country_code) > 3:
                raise ValidationError("Country code cannot exceed 3 characters.")
            # Ensure the country code exists in CustomCountry
            if not CustomCountry.objects.filter(country_code=country_code).exists():
                raise ValidationError(f"Country code '{country_code}' does not exist in CustomCountry.")
        return country_code

    def clean_gmt_offset_jan(self):
        gmt_offset_jan = self.cleaned_data.get('gmt_offset_jan')
        if gmt_offset_jan is None:
            raise ValidationError("GMT offset for January is required.")
        if not (-12.0 <= gmt_offset_jan <= 14.0):
            raise ValidationError("GMT offset for January must be between -12.0 and 14.0.")
        if round(gmt_offset_jan * 4) / 4 != gmt_offset_jan:
            raise ValidationError("GMT offset for January must be a multiple of 0.25.")
        return gmt_offset_jan

    def clean_dst_offset_jul(self):
        dst_offset_jul = self.cleaned_data.get('dst_offset_jul')
        if dst_offset_jul is None:
            raise ValidationError("DST offset for July is required.")
        if not (-12.0 <= dst_offset_jul <= 14.0):
            raise ValidationError("DST offset for July must be between -12.0 and 14.0.")
        if round(dst_offset_jul * 4) / 4 != dst_offset_jul:
            raise ValidationError("DST offset for July must be a multiple of 0.25.")
        return dst_offset_jul

    def clean_raw_offset(self):
        raw_offset = self.cleaned_data.get('raw_offset')
        if raw_offset is None:
            raise ValidationError("Raw offset is required.")
        if not (-12.0 <= raw_offset <= 14.0):
            raise ValidationError("Raw offset must be between -12.0 and 14.0.")
        if round(raw_offset * 4) / 4 != raw_offset:
            raise ValidationError("Raw offset must be a multiple of 0.25.")
        return raw_offset

    @transaction.atomic
    def save(self, commit=True, user=None):
        logger.debug(f"Saving TimezoneForm: {self.cleaned_data.get('timezone_id', 'New Timezone')}, user={user}")
        instance = super().save(commit=False)
        cache_key = f"timezone:{instance.timezone_id or 'new'}"
        try:
            redis_client.delete(cache_key)
            logger.debug(f"Invalidated cache for Timezone: {cache_key}")
        except redis.RedisError as e:
            logger.warning(f"Failed to invalidate cache for {cache_key}: {str(e)}")

        if user:
            if not instance.pk:
                instance.created_by = user
            instance.updated_by = user
        if commit:
            instance.save(user=user, skip_validation=False)
            logger.info(f"Saved Timezone: {instance.timezone_id} (ID: {instance.id})")
        return instance
