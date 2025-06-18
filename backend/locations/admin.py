from django import forms
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.utils import timezone

from .models import City, Country, GlobalRegion, State


# --- Reusable Deleted Status Filter ---
class DeletedStatusFilter(SimpleListFilter):
    title = 'Deleted Status'
    parameter_name = 'deleted_status'

    def lookups(self, request, model_admin):
        return (
            ('deleted', 'Deleted'),
            ('not_deleted', 'Not Deleted'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'deleted':
            return queryset.filter(deleted_at__isnull=False)
        if self.value() == 'not_deleted':
            return queryset.filter(deleted_at__isnull=True)
        return queryset


# --- City Admin Form ---
class CityAdminForm(forms.ModelForm):
    class Meta:
        model = City
        fields = ['country', 'state', 'name', 'postal_code', 'code']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically filter states based on selected country
        if 'country' in self.data:
            try:
                country_id = int(self.data.get('country'))
                self.fields['state'].queryset = State.objects.filter(
                    country_id=country_id).order_by('name')
            except (ValueError, TypeError):
                # Show no states if country is invalid
                self.fields['state'].queryset = State.objects.none()
        elif self.instance.pk and self.instance.country:
            self.fields['state'].queryset = State.objects.filter(
                country=self.instance.country).order_by('name')
        else:
            # Empty queryset if no country selected
            self.fields['state'].queryset = State.objects.none()


# --- Simplified Soft Delete and Restore Actions ---
def soft_delete_action(model_name):
    """Soft delete selected records by setting deleted_at timestamp."""
    @admin.action(description=f"Soft delete selected {model_name.lower()}s")
    def action(modeladmin, request, queryset):
        # Update deleted_at for active records
        updated = queryset.filter(deleted_at__isnull=True).update(deleted_at=timezone.now())
        modeladmin.message_user(request, f"{updated} {model_name.lower()}(s) soft deleted successfully.", messages.SUCCESS)
    action.__name__ = f"soft_delete_{model_name.lower()}"
    return action


def restore_action(model_name):
    """Restore selected records by clearing deleted_at timestamp."""
    @admin.action(description=f"Restore selected {model_name.lower()}s")
    def action(modeladmin, request, queryset):
        # Clear deleted_at for deleted records
        updated = queryset.filter(deleted_at__isnull=False).update(deleted_at=None)
        modeladmin.message_user(request, f"{updated} {model_name.lower()}(s) restored successfully.", messages.SUCCESS)
    action.__name__ = f"restore_{model_name.lower()}"
    return action


# --- Base Admin Class to Reduce Duplication ---
class BaseAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        # Dynamically include only fields that exist in the model
        possible_fields = [
            'created_at',
            'updated_at',
            'deleted_at',
            'created_by',
            'updated_by']
        return [field for field in possible_fields if field in [
            f.name for f in self.model._meta.fields]]

    def get_fields(self, request, obj=None):
        # Exclude audit fields from form; subclasses can override
        readonly_fields = self.get_readonly_fields(request, obj)
        return [
            f.name for f in self.model._meta.fields if f.name not in readonly_fields]

    def save_model(self, request, obj, form, change):
        # Only set created_by/updated_by if fields exist in the model
        if not obj.pk and 'created_by' in [
                f.name for f in self.model._meta.fields]:
            obj.created_by = request.user
        if 'updated_by' in [f.name for f in self.model._meta.fields]:
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def is_active(self, obj):
        return obj.deleted_at is None if hasattr(obj, 'deleted_at') else True
    is_active.boolean = True
    is_active.short_description = "Active"


# --- Global Region Admin ---
@admin.register(GlobalRegion)
class GlobalRegionAdmin(BaseAdmin):
    list_display = ('id', 'name', 'is_active')
    search_fields = ('id', 'name',)
    list_filter = ['name', DeletedStatusFilter]
    actions = [
        soft_delete_action("GlobalRegion"),
        restore_action("GlobalRegion")]

    def get_fields(self, request, obj=None):
        return ['name']


# --- Country Admin Form ---
class CountryAdminForm(forms.ModelForm):
    class Meta:
        model = Country
        fields = ['name', 'global_region', 'code']
        labels = {
            'name': 'Country Name',
            'code': 'Country Code',
            'global_region': 'Global Region'
        }
        # Specify a text input widget for the 'code' field
        widgets = {
            'code': forms.TextInput(attrs={'maxlength': '2', 'size': '10'}),
        }

    def clean_code(self):
        # Ensure the code is unique, respecting the model's unique=True
        # constraint
        code = self.cleaned_data.get('code')
        if code:
            # Check if another country has the same code, excluding the current
            # instance
            queryset = Country.objects.filter(code=code)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError(
                    "A country with this code already exists.")
        return code


# --- Country Admin ---
@admin.register(Country)
class CountryAdmin(BaseAdmin):
    form = CountryAdminForm
    list_display = (
        'id',
        'name',
        'get_country_code',
        'global_region',
        'is_active')
    list_filter = ['global_region', 'location_type', DeletedStatusFilter]
    search_fields = ('id', 'name', 'code')
    autocomplete_fields = ['global_region']
    actions = [soft_delete_action("Country"), restore_action("Country")]

    def get_readonly_fields(self, request, obj=None):
        return super().get_readonly_fields(request, obj)

    def get_country_code(self, obj):
        return obj.code if obj.code else "-"
    get_country_code.short_description = "Country Code"

    def get_fields(self, request, obj=None):
        return ['name', 'global_region', 'code']

    def save_model(self, request, obj, form, change):
        obj.location_type = 'country'
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return False


# --- State Admin Form ---
class StateAdminForm(forms.ModelForm):
    class Meta:
        model = State
        fields = ['name', 'country', 'code', 'location_type']
        labels = {
            'name': 'State Name',
            'code': 'State Code'
        }


# --- State Admin ---
@admin.register(State)
class StateAdmin(BaseAdmin):
    form = StateAdminForm
    list_display = (
        'id',
        'name',
        'get_state_code',
        'country',
        'get_location_type_display',
        'is_active')
    list_filter = ['location_type', DeletedStatusFilter]
    search_fields = ('id', 'name', 'code', 'country__name')
    autocomplete_fields = ['country']
    actions = [soft_delete_action("State"), restore_action("State")]

    def get_readonly_fields(self, request, obj=None):
        return super().get_readonly_fields(request, obj)

    def get_state_code(self, obj):
        return obj.code if obj.code else "-"
    get_state_code.short_description = "State Code"

    def get_location_type_display(self, obj):
        return obj.get_location_type_display()
    get_location_type_display.short_description = "Location Type"

    def get_fields(self, request, obj=None):
        return ['country', 'name', 'code']

    def save_model(self, request, obj, form, change):
        obj.location_type = 'state'
        super().save_model(request, obj, form, change)


# --- City Admin ---
@admin.register(City)
class CityAdmin(BaseAdmin):
    form = CityAdminForm
    list_display = (
        'id',
        'name',
        'state',
        'country',
        'postal_code',
        'get_location_type_display',
        'is_active')
    list_filter = ['location_type', DeletedStatusFilter]
    search_fields = (
        'id',
        'name',
        'postal_code',
        'country__name',
        'state__name')
    autocomplete_fields = ['country', 'state']
    actions = [soft_delete_action("City"), restore_action("City")]

    def get_readonly_fields(self, request, obj=None):
        return super().get_readonly_fields(request, obj)

    def get_location_type_display(self, obj):
        return obj.get_location_type_display()
    get_location_type_display.short_description = "Location Type"

    fieldsets = (
        (None, {
            'fields': ('country', 'state', 'name', 'postal_code'),
            'description': 'Enter the details for the city field. Ensure the country and state are correctly selected.'
        }),
    )

    def get_fields(self, request, obj=None):
        return ['country', 'state', 'name', 'postal_code']

    def save_model(self, request, obj, form, change):
        obj.location_type = 'city'
        super().save_model(request, obj, form, change)
