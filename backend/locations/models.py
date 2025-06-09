import re

from core.models import ActiveManager, TimeStampedModel
from django.core.exceptions import ValidationError
from django.db import models
from django_countries.fields import CountryField


class GlobalRegion(models.Model):

    """Geopolitical or cultural region like South-East Asia, Europe, Latin America."""

    name = models.CharField(max_length=128, unique=True)

    class Meta:
        verbose_name = "Global Region"
        verbose_name_plural = "Global Regions"

    def __str__(self):
        return self.name


class Country(models.Model):

    """Country model using ISO 3166-1 codes."""

    code = CountryField(unique=True)
    name = models.CharField(max_length=128)
    global_region = models.ForeignKey(
        GlobalRegion, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="e.g., South-East Asia, North America"
    )

    class Meta:
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    def __str__(self):
        return self.name


class State(models.Model):

    """Administrative division like State or Province."""

    name = models.CharField(max_length=128)
    code = models.CharField(max_length=10, help_text="State code, e.g., CA, MH")
    country = models.ForeignKey(Country, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('country', 'code')
        verbose_name = "State"
        verbose_name_plural = "States"

    def __str__(self):
        return f"{self.name}, {self.country.name}"


class City(TimeStampedModel):

    """City model supporting global addresses."""

    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)
    city = models.CharField(max_length=128)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    landmark = models.CharField(max_length=128, blank=True, null=True)

    created_by = models.ForeignKey(
        'auth.User', related_name='cities_created',
        on_delete=models.SET_NULL, null=True, blank=True
    )
    updated_by = models.ForeignKey(
        'auth.User', related_name='cities_updated',
        on_delete=models.SET_NULL, null=True, blank=True
    )

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['id']
        verbose_name = "City"
        verbose_name_plural = "Cities"
        indexes = [
            models.Index(fields=['country', 'city']),
            models.Index(fields=['postal_code']),
        ]

    def clean(self):
        """Validate postal code formats and country-state match."""
        if self.postal_code and self.country:
            if self.country.code == 'US' and not re.match(r'^\d{5}(-\d{4})?$', self.postal_code):
                raise ValidationError("Invalid US postal code format (e.g., 12345 or 12345-6789)")
            elif self.country.code == 'GB' and not re.match(r'^[A-Z0-9]{2,4}\s?[A-Z0-9]{3}$', self.postal_code):
                raise ValidationError("Invalid UK postal code format (e.g., SW1A 1AA)")

        if self.state and self.state.country != self.country:
            raise ValidationError("Selected state does not belong to the selected country.")

    def __str__(self):
        parts = [
            self.address_line1,
            self.address_line2,
            self.landmark,
            self.city,
            self.state.name if self.state else None,
            self.postal_code,
            self.country.name
        ]
        return ", ".join([p for p in parts if p])
