from django import forms
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.db.models import F
from django.utils import timezone
from locations.models import City, GlobalRegion, State

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

        # Validate dates are not in the future
        if from_date and from_date > today:
            self.add_error('from_date', 'From date cannot be in the future.')
        if to_date and to_date > today:
            self.add_error('to_date', 'To date cannot be in the future.')
        # Validate to_date is not before from_date
        if from_date and to_date and to_date < from_date:
            self.add_error('to_date', 'To date cannot be before from date.')

        return cleaned_data


class ClientOrganizationInline(admin.TabularInline):

    """Inline admin for ClientOrganization (Client > other_organizations)."""

    model = ClientOrganization
    form = ClientOrganizationInlineForm
    extra = 0
    can_delete = True
    verbose_name = 'Corporate Affiliation'
    verbose_name_plural = 'Corporate Affiliations'
    fields = ('organization', 'corporate_affiliation_city', 'from_date', 'to_date')
    autocomplete_fields = ['organization', 'corporate_affiliation_city']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == 'organization':
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
    fields = ('organization', 'corporate_affiliation_city', 'from_date', 'to_date')  # Hide client field
    autocomplete_fields = ['client', 'organization', 'corporate_affiliation_city']

    def get_affiliation_city(self, obj):
        """Display city name for corporate affiliation city."""
        return obj.corporate_affiliation_city.name if obj.corporate_affiliation_city else '-'
    get_affiliation_city.short_description = 'City'


class IsActiveFilter(SimpleListFilter):
    title = 'Active Status'
    parameter_name = 'is_active'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Active'),
            ('inactive', 'Soft Deleted'),
            ('all', 'All'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(is_active=True, deleted_at__isnull=True)
        if self.value() == 'inactive':
            return queryset.filter(is_active=False, deleted_at__isnull=False)
        return queryset

class ClientAdminForm(forms.ModelForm):

    """Custom form for Client admin."""

    class Meta:
        model = Client
        fields = '__all__'
        labels = {
            'current_organization': 'Current Organization',
            'current_org_joining_day': 'Joining Date',
            'current_org_city': 'Current Organization City',
            'current_country': 'Current Country',
            'current_state': 'Current State',
            'current_region': 'Current Region',
            'is_active': 'Is active?',
        }
        widgets = {
            'current_org_joining_day': forms.DateInput(attrs={'type': 'date'}),
            'is_active': forms.CheckboxInput(),
        }
        help_texts = {
            'is_active': 'Uncheck to soft-delete the client. Soft-deleted clients are hidden from default queries but can be restored.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set label for industry dropdown if field is included
        if 'current_industry' in self.fields:
            self.fields['current_industry'].label_from_instance = lambda obj: obj.name
        # Filter current_org_city based on current_organization
        if self.instance and self.instance.current_organization:
            self.fields['current_org_city'].queryset = self.instance.current_organization.cities.all()

    def clean(self):
        cleaned_data = super().clean()
        current_organization = cleaned_data.get('current_organization')
        current_org_city = cleaned_data.get('current_org_city')
        today = timezone.now().date()

        # Validate current_org_joining_day is not in the future
        current_org_joining_day = cleaned_data.get('current_org_joining_day')
        if current_org_joining_day and current_org_joining_day > today:
            self.add_error('current_org_joining_day', 'Joining date cannot be in the future.')

        # Auto-set current_industry from current_organization
        if current_organization and current_organization.industry:
            cleaned_data['current_industry'] = current_organization.industry
            self.instance.current_industry = current_organization.industry

        # Auto-set current_country, current_state, current_region from current_org_city
        if current_org_city:
            cleaned_data['current_country'] = current_org_city.country
            self.instance.current_country = current_org_city.country
            # Validate state and region selection
            state = State.objects.filter(country=current_org_city.country).first()
            if not state:
                self.add_error('current_org_city', 'No state found for the selected city’s country.')
            cleaned_data['current_state'] = state
            self.instance.current_state = state
            # Use a more specific region selection logic
            region = GlobalRegion.objects.filter(country=current_org_city.country).first()
            if not region:
                self.add_error('current_org_city', 'No global region found for the selected city’s country.')
            cleaned_data['current_region'] = region
            self.instance.current_region = region

        return cleaned_data


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):

    """Admin for Client model."""

    form = ClientAdminForm
    list_display = ('id', 'name', 'email', 'get_current_organization', 'get_current_org_city', 'get_other_organizations',
                    'get_current_industry', 'created_at', 'updated_at', 'is_active', 'deleted_at')
    search_fields = ('name', 'email', 'current_organization__name', 'other_organizations__name', 'current_industry__name')
    readonly_fields = ('created_at', 'updated_at', 'current_industry', 'current_region', 'current_country', 'current_state')
    list_filter = ('current_industry__name', 'created_at', IsActiveFilter, 'deleted_at')
    ordering = ('-created_at',)
    inlines = [ClientOrganizationInline]
    fields = ('name', 'email', 'phone', 'current_organization', 'current_org_joining_day', 'current_org_city', 'is_active')

    def soft_delete(self, request, queryset):
        """Mark selected clients as soft-deleted by setting is_active=False and updating deleted_at."""
        updated = queryset.update(is_active=False, deleted_at=timezone.now())
        self.message_user(request, f"{updated} client(s) successfully soft-deleted.", messages.SUCCESS)
    soft_delete.short_description = "Soft delete selected clients"

    def restore(self, request, queryset):
        """Restore selected clients by setting is_active=True and clearing deleted_at."""
        updated = queryset.update(is_active=True, deleted_at=None)
        self.message_user(request, f"{updated} client(s) successfully restored.", messages.SUCCESS)
    restore.short_description = "Restore selected clients"

    def get_current_organization(self, obj):
        """Display current organization name."""
        return obj.current_organization.name if obj.current_organization else '-'
    get_current_organization.short_description = 'Current Organization'

    def get_current_org_city(self, obj):
        """Display current organization city name."""
        return obj.current_org_city.name if obj.current_org_city else '-'
    get_current_org_city.short_description = 'Current City'

    def get_other_organizations(self, obj):
        """Display other organizations with their industries."""
        other_organizations = [
            f"{co.organization.name} ({co.organization.industry.name})"
            if co.organization.industry else co.organization.name
            for co in obj.clientorganization_set.exclude(organization=obj.current_organization)
        ]
        return ', '.join(other_organizations) if other_organizations else '-'
    get_other_organizations.short_description = 'Other Organizations'

    def get_current_industry(self, obj):
        """Display current industry name."""
        return obj.current_industry.name if obj.current_industry else '-'
    get_current_industry.short_description = 'Current Industry'

    def get_queryset(self, request):
        return Client.all_objects.all()  # Show all clients, including soft-deleted


class OrganizationAdminForm(forms.ModelForm):

    """Custom form for Organization admin."""

    cities = forms.ModelMultipleChoiceField(
        queryset=City.objects.all(),
        widget=forms.SelectMultiple,
        required=False,
        label='Organization Offices',
        help_text='List of cities where this organization has offices (including head office).',
    )

    class Meta:
        model = Organization
        fields = '__all__'
        labels = {
            'headquarter_city': 'Head Quarter',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cities'].label_from_instance = lambda obj: obj.name
        self.fields['industry'].required = True  # Make industry mandatory

    def clean(self):
        cleaned_data = super().clean()
        cities = cleaned_data.get('cities')
        headquarter_city = cleaned_data.get('headquarter_city')
        # Ensure headquarter_city is in cities
        if headquarter_city and headquarter_city not in cities:
            cleaned_data['cities'] = list(cities) + [headquarter_city]
            self.instance.cities.set(cleaned_data['cities'])
        return cleaned_data


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):

    """Admin for Organization model."""

    form = OrganizationAdminForm
    list_display = ('id', 'name', 'get_current_industry', 'get_head_office', 'get_cities', 'created_at', 'updated_at')
    search_fields = ('name', 'industry__name', 'headquarter_city__name', 'cities__name')
    fields = ('name', 'industry', 'headquarter_city', 'cities')

    def get_current_industry(self, obj):
        """Display industry name."""
        return obj.industry.name if obj.industry else '-'
    get_current_industry.short_description = 'Current Industry'

    def get_head_office(self, obj):
        """Display headquarter city name."""
        return obj.headquarter_city.name if obj.headquarter_city else '-'
    get_head_office.short_description = 'Headquarter City'

    def get_cities(self, obj):
        """Display list of organization office cities."""
        return ', '.join(city.name for city in obj.cities.all())
    get_cities.short_description = 'Organization Offices'


class IndustryAdminForm(forms.ModelForm):

    """Custom form for Industry admin to make global_region required."""

    class Meta:
        model = Industry
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['global_region'].required = True  # Make global_region mandatory


@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):

    """Admin for Industry model."""

    form = IndustryAdminForm
    list_display = ['id', 'name', 'get_global_region', 'created_at', 'updated_at']
    fields = ['name', 'global_region']
    search_fields = ['name', 'global_region__name']
    readonly_fields = ['created_at', 'updated_at']
    exclude = ['deleted_at']

    def get_global_region(self, obj):
        """Display global region name."""
        return obj.global_region.name if obj.global_region else '-'
    get_global_region.short_description = 'Global Region'
