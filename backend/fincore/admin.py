import logging

from core.admin_mixins import AdminIconDecorator, BaseAdmin
from django import forms
from django.apps import apps
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from fincore.models.address import Address
from fincore.models.contact import Contact
from fincore.models.entity_mapping import FincoreEntityMapping
from fincore.models.tax_profile import TaxProfile

logger = logging.getLogger(__name__)

class AddressAdminForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = '__all__'
        Address._meta.verbose_name = "Business Address"
        Address._meta.verbose_name_plural = "Business Addresses"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'entity_mapping' in self.fields:
            self.fields['entity_mapping'].label_from_instance = lambda obj: (
                apps.get_model('entities', 'Entity').objects.get(id=obj.entity_id).name
                if obj.entity_type == 'entities.Entity' else str(obj)
            )

@AdminIconDecorator.register_with_icon(Address)
class AddressAdmin(BaseAdmin):

    """Admin configuration for the Address model."""

    icon='fas fa-map-marker-alt'
    form = AddressAdminForm
    list_display = ('entity_mapping_link', 'entity_address', 'address_type', 'city', 'country', 'is_default', 'is_active')
    list_filter = ('address_type', 'country', 'region', 'subregion', 'created_by')
    search_fields = ('street_address', 'postal_code', 'city__name', 'country__name', 'region__name', 'subregion__name')
    list_editable = ('is_default',)
    date_hierarchy = 'created_at'
    list_per_page = 50
    autocomplete_fields = ['entity_mapping', 'city', 'country', 'region', 'subregion']
    actions = ['soft_delete', 'restore']
    select_related_fields = ['entity_mapping', 'city__subregion__region__country', 'created_by', 'updated_by', 'deleted_by']

    base_fieldsets_config = [
        (None, {
            'fields': ('address_type', 'street_address', 'city', 'postal_code')
        }),
        (_('Location Details'), {
            'fields': ('country', 'region', 'subregion', 'is_default')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def entity_mapping_link(self, obj):
        if obj.entity_mapping and obj.entity_mapping.entity_type == 'entities.Entity':
            try:
                Entity = apps.get_model('entities', 'Entity')
                entity = Entity.objects.get(id=obj.entity_mapping.entity_id)
                url = reverse('admin:entities_entity_change', args=[entity.pk])
                return format_html('<a href="{}">{}</a>', url, entity.name)
            except Entity.DoesNotExist:
                return '-'
        return '-'
    entity_mapping_link.short_description = 'Business Name'

    def entity_address(self, obj):
        url = reverse('admin:fincore_address_change', args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, obj.get_full_address())
    entity_address.short_description = 'Business Address'

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

class ContactAdminForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'entity_mapping' in self.fields:
            self.fields['entity_mapping'].label_from_instance = lambda obj: (
                apps.get_model('entities', 'Entity').objects.get(id=obj.entity_id).name
                if obj.entity_type == 'entities.Entity' else str(obj)
            )


@AdminIconDecorator.register_with_icon(Contact)
class ContactAdmin(BaseAdmin):

    """Admin configuration for the Contact model."""

    icon='fas fa-address-book'
    form = ContactAdminForm
    list_display = ('name_link', 'entity_mapping_link', 'email', 'phone_number', 'role', 'country', 'is_primary', 'is_active')
    list_filter = ('role', 'country', 'is_primary', 'created_by')
    search_fields = ('name', 'email', 'phone_number')
    list_editable = ('is_primary',)
    date_hierarchy = 'created_at'
    list_per_page = 50
    autocomplete_fields = ['entity_mapping', 'country']
    actions = ['soft_delete', 'restore']
    select_related_fields = ['entity_mapping', 'country', 'created_by', 'updated_by', 'deleted_by']

    base_fieldsets_config = [
        (None, {
            'fields': ( 'name', 'email', 'phone_number', 'role')
        }),
        (_('Details'), {
            'fields': ('country', 'is_primary')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def name_link(self, obj):
        url = reverse('admin:fincore_contact_change', args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, obj.name)
    name_link.short_description = 'Name'

    def entity_mapping_link(self, obj):
        if obj.entity_mapping and obj.entity_mapping.entity_type == 'entities.Entity':
            try:
                Entity = apps.get_model('entities', 'Entity')
                entity = Entity.objects.get(id=obj.entity_mapping.entity_id)
                url = reverse('admin:entities_entity_change', args=[entity.pk])
                return format_html('<a href="{}">{}</a>', url, entity.name)
            except Entity.DoesNotExist:
                return '-'
        return '-'
    entity_mapping_link.short_description = 'Business Name'

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

class TaxProfileAdminForm(forms.ModelForm):
    class Meta:
        model = TaxProfile
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'entity_mapping' in self.fields:
            self.fields['entity_mapping'].label_from_instance = lambda obj: (
                apps.get_model('entities', 'Entity').objects.get(id=obj.entity_id).name
                if obj.entity_type == 'entities.Entity' else str(obj)
            )

@AdminIconDecorator.register_with_icon(TaxProfile)
class TaxProfileAdmin(BaseAdmin):

    """Admin configuration for the TaxProfile model."""

    icon='fas fa-file-invoice'
    form = TaxProfileAdminForm
    list_display = ('tax_identifier', 'tax_identifier_type', 'entity_mapping_link', 'country', 'is_tax_exempt', 'is_active')
    list_filter = ('tax_identifier_type', 'country', 'region', 'is_tax_exempt', 'created_by')
    search_fields = ('tax_identifier', 'tax_exemption_reason', 'country__name')
    date_hierarchy = 'created_at'
    list_per_page = 50
    autocomplete_fields = ['entity_mapping', 'country', 'region']
    actions = ['soft_delete', 'restore']
    select_related_fields = ['entity_mapping', 'country', 'region', 'created_by', 'updated_by', 'deleted_by']

    base_fieldsets_config = [
        (None, {
            'fields': ( 'tax_identifier', 'tax_identifier_type', 'is_tax_exempt')
        }),
        (_('Details'), {
            'fields': ('tax_exemption_reason', 'tax_exemption_document', 'country', 'region')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def entity_mapping_link(self, obj):
        if obj.entity_mapping and obj.entity_mapping.entity_type == 'entities.Entity':
            try:
                Entity = apps.get_model('entities', 'Entity')
                entity = Entity.objects.get(id=obj.entity_mapping.entity_id)
                url = reverse('admin:entities_entity_change', args=[entity.pk])
                return format_html('<a href="{}">{}</a>', url, entity.name)
            except Entity.DoesNotExist:
                return '-'
        return '-'
    entity_mapping_link.short_description = 'Business Name'

    @admin.display(description='Tax Identifier')
    def tax_identifier(self, obj):
        return obj.tax_identifier

    @admin.display(description='Tax Identifier Type')
    def tax_identifier_type(self, obj):
        return obj.tax_identifier_type

    @admin.display(description='Is Tax Exempt')
    def is_tax_exempt(self, obj):
        return obj.is_tax_exempt
    is_tax_exempt.boolean = True

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


@AdminIconDecorator.register_with_icon(FincoreEntityMapping)
class FincoreEntityMappingAdmin(BaseAdmin):

    """Minimal admin configuration for FincoreEntityMapping to support autocomplete without UI visibility."""

    icon='fas fa-project-diagram'
    list_display = ('id', 'entity_uuid', 'entity_type', 'entity_id', 'is_active')
    list_filter = ('entity_type',)
    search_fields = ('entity_uuid', 'entity_type', 'entity_id', 'content_type')
    readonly_fields = ('entity_uuid', 'entity_type', 'entity_id', 'content_type', 'created_at', 'updated_at')
    list_per_page = 50

    base_fieldsets_config = [
        (None, {
            'fields': ('entity_uuid', 'entity_type', 'entity_id', 'content_type')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def has_module_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
