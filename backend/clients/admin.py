from django import forms
from django.contrib import admin
from django.db.models import F
from django.utils import timezone

from .models import Client, ClientOrganization, Industry, Organization


class ClientOrganizationInlineForm(forms.ModelForm):

    """Form for inline editing of ClientOrganization in the admin."""

    class Meta:
        model = ClientOrganization
        fields = '__all__'
        widgets = {
            'from_date': forms.DateInput(attrs={'type': 'date'}),
            'to_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        from_date = cleaned_data.get('from_date')
        to_date = cleaned_data.get('to_date')
        today = timezone.now().date()

        if from_date and from_date > today:
            self.add_error('from_date', 'From date cannot be in the future.')
        if to_date and to_date > today:
            self.add_error('to_date', 'To date cannot be in the future.')

        return cleaned_data


class ClientOrganizationInline(admin.TabularInline):

    """Inline admin for ClientOrganization (Client > other_companies)."""

    model = ClientOrganization
    form = ClientOrganizationInlineForm
    extra = 0
    can_delete = True
    verbose_name = "Corporate Affiliation"
    verbose_name_plural = "Corporate Affiliations"
    fields = ('organization', 'corporate_affiliation_city', 'from_date', 'to_date')
    autocomplete_fields = ['organization', 'corporate_affiliation_city']

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "organization":
            field.widget.can_change_related = False
            field.widget.can_add_related = False
            field.widget.can_delete_related = False
        return field

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.exclude(organization=F('client__current_organization'))


@admin.register(ClientOrganization)
class ClientOrganizationAdmin(admin.ModelAdmin):

    """Standalone admin for ClientOrganization."""

    list_display = ('id', 'client', 'organization', 'get_affiliation_city', 'from_date', 'to_date')
    fields = ('client', 'organization', 'corporate_affiliation_city', 'from_date', 'to_date')
    autocomplete_fields = ['client', 'organization', 'corporate_affiliation_city']

    def get_affiliation_city(self, obj):
        """Display only the city name for corporate affiliation city."""
        return obj.corporate_affiliation_city.city if obj.corporate_affiliation_city else "-"
    get_affiliation_city.short_description = "City"


class ClientForm(forms.ModelForm):

    """Custom form for Client admin."""

    class Meta:
        model = Client
        fields = '__all__'
        labels = {
            'current_organization': 'Current Organization:',
            'current_org_joining_day': 'Joining Date:',
            'current_org_city': 'Current Organization City:',
            'current_country': 'Current Country:',
            'current_state': 'Current State:',
            'current_region': 'Current Region:',
        }
        widgets = {
            'current_org_joining_day': forms.DateInput(attrs={'type': 'date'}),
        }


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):

    """Admin for Client model."""

    form = ClientForm
    list_display = (
        'id', 'name', 'email', 'get_current_organization',
        'get_current_org_city', 'get_other_companies',
        'created_at', 'updated_at'
    )
    search_fields = (
        'name', 'email', 'current_organization__name',
        'other_orgs__name', 'industry__name'
    )
    readonly_fields = ('created_at', 'updated_at')
    list_filter = ('industry__name', 'created_at')
    ordering = ('-created_at',)
    inlines = [ClientOrganizationInline]
    fields = (
        'name', 'email', 'phone', 'current_organization',
        'current_org_joining_day', 'current_org_city',
        'current_country', 'current_state', 'current_region',
        'industry'
    )

    def get_current_organization(self, obj):
        return obj.current_organization.name if obj.current_organization else "-"
    get_current_organization.short_description = "Current Organization"

    def get_current_org_city(self, obj):
        """Display only the city name for the current organization city."""
        return obj.current_org_city.city if obj.current_org_city else "-"
    get_current_org_city.short_description = "Current City"

    def get_other_companies(self, obj):
        other_companies = [
            f"{co.organization.name} ({co.organization.industry.name})"
            if co.organization.industry else co.organization.name
            for co in obj.clientorganization_set.exclude(organization=obj.current_organization)
        ]
        return ", ".join(other_companies) if other_companies else "-"
    get_other_companies.short_description = "Other Companies"


class OrganizationForm(forms.ModelForm):

    """Custom form for Organization admin."""

    class Meta:
        model = Organization
        fields = '__all__'
        labels = {
            'current_org_head_office': 'Head Office',
            'current_org_city': 'Current Organization City'
        }


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):

    """Admin for Organization model."""

    form = OrganizationForm
    list_display = ('id', 'name', 'get_industry', 'get_head_office', 'created_at', 'updated_at')
    search_fields = ('name', 'industry__name', 'current_org_head_office__city', 'current_org_city__city')
    fields = ('name', 'industry', 'current_org_head_office', 'current_org_city')

    def get_industry(self, obj):
        return obj.industry.name if obj.industry else "-"
    get_industry.short_description = 'Industry'

    def get_head_office(self, obj):
        """Display only the city name for the head office."""
        return obj.current_org_head_office.city if obj.current_org_head_office else "-"
    get_head_office.short_description = 'Head Office'


@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):

    """Admin for Industry model."""

    list_display = ('id', 'name', 'created_at', 'updated_at')
    search_fields = ['name']
    readonly_fields = ('created_at', 'updated_at')
    exclude = ['deleted_at']
