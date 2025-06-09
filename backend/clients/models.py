from core.models import ActiveManager, TimeStampedModel
from django.db import models
from locations.models import City, Country, GlobalRegion, State


class Industry(TimeStampedModel):

    """Model for an industry."""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=128, unique=True, default='uncategorized')

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['id']
        verbose_name = "Industry"
        verbose_name_plural = "Industries"

    def __str__(self):
        return self.name


class Organization(TimeStampedModel):

    """Model for an organization."""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, default='uncategorized')
    industry = models.ForeignKey(Industry, on_delete=models.SET_NULL, null=True, blank=True)
    current_org_head_office = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='org_current_head_office'
    )
    current_org_city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='org_current_city'
    )

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['id']
        verbose_name = "Organization"
        verbose_name_plural = "Organization Dashboard"

    def __str__(self):
        return self.name


class ClientOrganization(models.Model):

    """Model for client-organization affiliation."""

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
        verbose_name = "Corporate Affiliation"
        verbose_name_plural = "Corporate Affiliations"
        unique_together = ('client', 'organization', 'from_date')

    def __str__(self):
        return f"{self.client.name} - {self.organization.name}"


class Client(TimeStampedModel):

    """Model for a client."""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=100, unique=True)
    phone = models.CharField(max_length=15, blank=True)

    current_organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='client_current_organization'
    )
    current_org_city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    current_org_joining_day = models.DateField(null=True, blank=True)

    # Location granularity fields
    current_country = models.ForeignKey(
        Country,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clients'
    )
    current_state = models.ForeignKey(
        State,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clients'
    )
    current_region = models.ForeignKey(
        GlobalRegion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clients'
    )

    other_orgs = models.ManyToManyField(
        Organization,
        through='ClientOrganization',
        related_name='other_organizations',
        blank=True
    )
    industry = models.ForeignKey(
        Industry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['id']
        verbose_name = "Client"
        verbose_name_plural = "Client Dashboard"

    def __str__(self):
        return self.name
