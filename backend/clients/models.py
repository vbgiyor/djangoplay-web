from core.models import ActiveManager, TimeStampedModel
from django.conf import settings  # Custom User model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from locations.models import City, Country, GlobalRegion, State, validate_postal_code, validate_state_country_match


class Industry(TimeStampedModel):

    """Model representing an industry."""

    name = models.CharField(max_length=128, default='uncategorized')
    global_region = models.ForeignKey(
        GlobalRegion,
        on_delete=models.PROTECT,
        null=False,
        blank=False,
        related_name='industries',
        help_text="Select the global region to which this industry belongs."
    )

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:

        """Metadata for Industry model."""

        ordering = ['id']
        verbose_name = "Industry"
        verbose_name_plural = "Industries"
        unique_together = ['name', 'global_region']

    def __str__(self):
        """String representation of Industry."""
        return f"{self.name}"


class Organization(TimeStampedModel):

    """Model representing an organization."""

    name = models.CharField(max_length=255, default='uncategorized')
    industry = models.ForeignKey(Industry, on_delete=models.PROTECT, null=False, blank=False)
    headquarter_city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        null=False,
        blank=False,
        related_name="headquarter_city_of_organization",
        help_text="The city where the organization's head office is located."
    )
    cities = models.ManyToManyField(
        City,
        related_name="organizations_with_offices",
        blank=True,
        help_text="List of cities where this organization has offices (including head office)."
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='organizations_created',
        on_delete=models.SET_NULL, null=True, blank=True
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='organizations_updated',
        on_delete=models.SET_NULL, null=True, blank=True
    )

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:

        """Metadata for Organization model."""

        ordering = ['id']
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

    def clean(self):
        """Validate headquarter city is in cities list."""
        if self.headquarter_city and self.headquarter_city not in self.cities.all():
            raise ValidationError("Headquarter city must be included in the list of cities.")

    def __str__(self):
        """String representation of Organization."""
        return self.name


class ClientOrganization(models.Model):

    """Model representing a client's affiliation with an organization."""

    client = models.ForeignKey('Client', on_delete=models.CASCADE)
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE)
    from_date = models.DateField(null=True, blank=True)
    to_date = models.DateField(null=True, blank=True)
    corporate_affiliation_city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:

        """Metadata for ClientOrganization model."""

        verbose_name = "Corporate Affiliation"
        verbose_name_plural = "Corporate Affiliations"
        unique_together = ('client', 'organization', 'from_date')

    def clean(self):
        """Validate dates and postal code."""
        if self.from_date and self.to_date and self.from_date > self.to_date:
            raise ValidationError("from_date cannot be after to_date.")
        if self.corporate_affiliation_city and self.corporate_affiliation_city.postal_code:
            validate_postal_code(
                self.corporate_affiliation_city.postal_code,
                self.corporate_affiliation_city.country.code)

    def __str__(self):
        """String representation of ClientOrganization."""
        return f"{self.client.name} - {self.organization.name}"


class Client(TimeStampedModel):

    """Represents a client with current and historical organization details."""

    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=100, unique=True)
    phone = models.CharField(max_length=15, blank=True)
    is_active = models.BooleanField(default=True)
    current_region = models.ForeignKey(
        GlobalRegion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_in_region"
    )
    current_country = models.ForeignKey(
        Country,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_in_country"
    )
    current_state = models.ForeignKey(
        State,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_in_state"
    )
    current_org_city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_working_in_this_city",
        help_text="The city where the client is currently working or has worked for the organization."
    )
    other_organizations = models.ManyToManyField(
        Organization,
        through='ClientOrganization',
        related_name='other_organizations',
        blank=True
    )
    current_industry = models.ForeignKey(
        Industry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_industry'
    )
    current_organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_organization'
    )
    current_org_joining_day = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='clients_created',
        on_delete=models.SET_NULL, null=True, blank=True
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='clients_updated',
        on_delete=models.SET_NULL, null=True, blank=True
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:

        """Metadata for Client model."""

        ordering = ['id']
        verbose_name = "Client"
        verbose_name_plural = "Client Dashboard"

    def clean(self):
        """Validate state-country match, organization city, industry, and postal code."""
        if self.current_state and self.current_country:
            validate_state_country_match(self.current_state, self.current_country)
        if self.current_org_city and self.current_organization and self.current_org_city not in self.current_organization.cities.all():
            raise ValidationError("Current organization city must be one of the organization's cities.")
        if self.current_organization and self.current_industry and self.current_organization.industry != self.current_industry:
            raise ValidationError("Industry does not match the current organization's industry.")
        if self.current_org_city and self.current_org_city.postal_code:
            validate_postal_code(self.current_org_city.postal_code, self.current_org_city.country.code)

    def __str__(self):
        """String representation of Client."""
        return self.name

    def save(self, *args, **kwargs):
        """Update deleted_at based on is_active status."""
        if not self.is_active and self.deleted_at is None:
            self.deleted_at = timezone.now()
        elif self.is_active and self.deleted_at is not None:
            self.deleted_at = None
        super().save(*args, **kwargs)
