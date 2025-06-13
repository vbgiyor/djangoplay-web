import re

from core.models import ActiveManager, TimeStampedModel
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django_countries.fields import CountryField


def validate_postal_code(postal_code, country_code):
    """Validate postal code based on country-specific formats."""
    patterns = {
        'US': r'^\d{5}(-\d{4})?$',  # US: 5 digits or 5+4
        'IN': r'^\d{6}$',           # India: 6 digits
        'CA': r'^[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d$',  # Canada: A1A 1A1
        'GB': r'^[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}$',     # UK: SW1A 1AA
        # Add more country patterns as needed
    }
    pattern = patterns.get(country_code, r'.*')  # Default to any string if no pattern
    if not re.match(pattern, postal_code):
        raise ValidationError(f"Invalid postal code format for {country_code}.")

def validate_state_country_match(state, country):
    """Ensure state belongs to the country if both are provided."""
    if state and country and state.country != country:
        raise ValidationError("State does not belong to the selected country.")

class LocationBase(TimeStampedModel):

    """Base model for location-related fields like `location_type` and `code`."""

    location_type = models.CharField(
        max_length=10,
        choices=[('country', 'Country'), ('state', 'State'), ('city', 'City')]
    )
    code = models.CharField(max_length=10, blank=True, null=True)  # Increased max_length for flexibility
    name = models.CharField(max_length=128)  # Added for consistency
    created_by = models.ForeignKey(
        User, related_name='%(class)s_created',
        on_delete=models.SET_NULL, null=True, blank=True
    )
    updated_by = models.ForeignKey(
        User, related_name='%(class)s_updated',
        on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

class GlobalRegion(models.Model):

    """Geopolitical or cultural region like South-East Asia, Europe, Latin America."""

    regions_data = [
        'East Asia & Pacific',
        'Europe & Central Asia',
        'Latin America & the Caribbean',
        'Middle East & North Africa',
        'South Asia',
        'Sub-Saharan Africa',
        'North America'
    ]

    name = models.CharField(
        max_length=128,
        unique=True,
        choices=[(region, region) for region in regions_data]
    )

    class Meta:
        ordering = ['id']
        verbose_name = "Global Region"
        verbose_name_plural = "Global Regions"

    def __str__(self):
        return self.name

class Country(LocationBase):

    """Country model using ISO 3166-1 codes."""

    code = CountryField(unique=True)
    global_region = models.ForeignKey(
        GlobalRegion, on_delete=models.PROTECT, null=False, blank=False,
        help_text="e.g., South-East Asia, North America"
    )

    class Meta:
        ordering = ['id']
        verbose_name = "Country"
        verbose_name_plural = "Countries"

class State(LocationBase):

    """Administrative division like State or Province."""

    country = models.ForeignKey(Country, on_delete=models.CASCADE)

    class Meta:
        ordering = ['id']
        unique_together = ('country', 'name')
        verbose_name = "State"
        verbose_name_plural = "States"

    def __str__(self):
        return f"{self.name}, {self.country.name}"

class City(LocationBase):

    """City model supporting global addresses."""

    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    state = models.ForeignKey(State, on_delete=models.PROTECT, null=False, blank=False)
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['id']
        verbose_name = "City"
        verbose_name_plural = "Cities"
        unique_together = ('country', 'state', 'name')
        indexes = [
            models.Index(fields=['country', 'name']),
            models.Index(fields=['postal_code']),
        ]

    def get_location_info(self):
        """Return the country, state, city, and postal code."""
        if not self.name or not self.state or not self.country:
            return None
        parts = [self.name, self.state.name, self.country.name]
        if self.postal_code:
            parts.append(self.postal_code)
        return ", ".join(parts)

    def clean(self):
        """Validate postal code formats and country-state match."""
        if self.postal_code and self.country:
            validate_postal_code(self.postal_code, self.country.code)
        validate_state_country_match(self.state, self.country)

    def add_or_get_city(self, city_name, state_name, country_name, postal_code=None):
        """Add or get city based on postal code and country/state context."""
        country = Country.objects.filter(name=country_name).first()
        if not country:
            raise ValidationError("Country does not exist.")

        state = State.objects.filter(name=state_name, country=country).first()
        if not state:
            state = State.objects.create(name=state_name, country=country, location_type='state')

        city = City.objects.filter(name=city_name, state=state, country=country).first()
        if not city:
            city = City.objects.create(
                name=city_name,
                state=state,
                country=country,
                postal_code=postal_code,
                location_type='city'
            )

        return city
