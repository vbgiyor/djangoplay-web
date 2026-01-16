import logging

from core.admin_mixins import AdminIconDecorator, BaseAdmin
from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from locations.utils.location_filters import *
from users.utils.helpers import user_is_verified_employee

from entities.models.entity import Entity

logger = logging.getLogger(__name__)

class EntityAdminForm(forms.ModelForm):
    class Meta:
        model = Entity
        fields = '__all__'
        widgets = {'website': forms.TextInput(attrs={'id': 'website_field'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        w = self.fields.get('website')
        if w:
            w.widget.attrs['value'] = self.instance.website if (self.instance and self.instance.website) else ""
            w.widget.attrs['placeholder'] = "Entity's website URL."


@AdminIconDecorator.register_with_icon(Entity)
class EntityAdmin(BaseAdmin):
    model = Entity
    form = EntityAdminForm

    list_display = (
        'name_display', 'headquarter_location', 'country',
        'entity_type', 'status_display', 'slug', 'display_ext_id',
        'industry_display', 'parent_entity_display', 'is_active'
    )
    # list_filter = ('entity_type', 'status', 'industry')
    search_fields = ('name', 'slug', 'external_id', 'registration_number', 'notes', 'website')
    list_editable = ()
    list_display_links = ('name_display',)
    date_hierarchy = 'created_at'
    ordering = ('-id',)

    select_related_fields = [
        'industry', 'default_address__city__subregion__region__country',
        'parent', 'created_by', 'updated_by', 'deleted_by'
    ]
    prefetch_related_fields = ['children']
    autocomplete_fields = ['default_address', 'industry', 'parent']
    actions = ['soft_delete', 'restore']

    base_fieldsets_config = [
        (None, {'fields': ('name', 'slug', 'entity_type', 'status', 'website')}),
        (_('Details'), {'fields': ('registration_number', 'entity_size', 'industry', 'default_address', 'parent', 'notes')}),
    ]


    # Add a display method for status
    @admin.display(description=_('Status'))
    def status_display(self, obj):
        return obj.get_status_display()  # Shows "Active", "Pending", etc.

    def queryset(self, request, queryset):
        if not self.value():
            return queryset

        model = queryset.model

        # Direct FK
        if hasattr(model, 'country'):
            return queryset.filter(country_id=self.value())

        # Region → Country
        if hasattr(model, 'region'):
            return queryset.filter(region__country_id=self.value())

        # SubRegion → Region → Country
        if hasattr(model, 'subregion'):
            return queryset.filter(subregion__region__country_id=self.value())

        # City → SubRegion → Region → Country
        if hasattr(model, 'city'):
            return queryset.filter(city__subregion__region__country_id=self.value())

        # Timezone special case
        from locations.models import CustomCountry
        if model.__name__ == "Timezone":
            cc = CustomCountry.objects.get(id=self.value()).country_code
            return queryset.filter(country_code=cc)

        # ENTITY special case
        if model.__name__ == "Entity":
            return queryset.filter(
                default_address__city__subregion__region__country_id=self.value()
            )

        return queryset

    def get_fieldset_conditions(self, request, obj=None):
        return []

    @admin.display(description=_('Name'))
    def name_display(self, obj):
        return format_html('<a href="{}">{}</a>', reverse('admin:entities_entity_change', args=[obj.pk]), obj.name)

    @admin.display(description=_('Headquarter'))
    def headquarter_location(self, obj):
        return obj.get_headquarter_location()

    @admin.display(description=_('Country'))
    def country(self, obj):
        return obj.get_country()

    @admin.display(description=_('Industry'))
    def industry_display(self, obj):
        return obj.industry.description if obj.industry else '-'

    @admin.display(description=_('Parent Entity'))
    def parent_entity_display(self, obj):
        return (
            format_html('<a href="{}">{}</a>', reverse('admin:entities_entity_change', args=[obj.parent.pk]), obj.parent.name)
            if obj.parent else '-'
        )

    @admin.display(description=_('Ext ID'))
    def display_ext_id(self, obj):
        return obj.external_id or '-'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'default_address' in form.base_fields:
            form.base_fields['default_address'].label_from_instance = (
                lambda dd: dd.get_full_address() if getattr(dd, 'entity_mapping', None) and dd.entity_mapping.entity_type == 'entities.Entity' else '-'
            )
        return form

    def get_model_perms(self, request):
        perms = super().get_model_perms(request)
        perms['index'] = True
        return perms

    def get_list_filter(self, request):
        base_filters = [IsActiveFilter]

        if user_is_verified_employee(request):
            base_filters.insert(0, CountryFilter)

        return base_filters


# import logging
# from django.contrib import admin
# from django.utils.translation import gettext_lazy as _
# from django.urls import reverse
# from django.utils.html import format_html
# from  paystream.custom_site.admin_site import admin_site
# from entities.models.entity import Entity
# from core.admin_mixins import BaseAdmin
# from core.admin_mixins import AdminIconDecorator
# from locations.models import CustomCountry
# from django.contrib.admin import SimpleListFilter
# from django import forms

# logger = logging.getLogger(__name__)

# class CountryFilter(SimpleListFilter):
#     title = 'country'
#     parameter_name = 'country'

#     def lookups(self, request, model_admin):
#         countries = CustomCountry.objects.all()
#         return [(country.id, country.name) for country in countries]

#     def queryset(self, request, queryset):
#         if self.value():
#             return queryset.filter(
#                 default_address__city__subregion__region__country__id=self.value()
#             )
#         return queryset

# class EntityAdminForm(forms.ModelForm):
#     class Meta:
#         model = Entity
#         fields = '__all__'
#         widgets = {
#             'website': forms.TextInput(attrs={'id': 'website_field'}),
#         }

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         if 'website' in self.fields:
#             if self.instance and self.instance.website:
#                 self.fields['website'].widget.attrs['value'] = self.instance.website
#             else:
#                 self.fields['website'].widget.attrs['placeholder'] = "Entity's website URL."

# @AdminIconDecorator.register_with_icon(Entity)
# class EntityAdmin(BaseAdmin):
#     """Admin configuration for the Entity model."""
#     # icon = 'fas fa-building-columns'
#     model = Entity
#     form = EntityAdminForm

#     list_display = ('name_display', 'headquarter_location', 'country', 'entity_type', 'status', 'slug', 'display_ext_id', 'industry_display', 'parent_entity_display', 'is_active')
#     list_filter = ('entity_type', 'status', 'industry', CountryFilter)
#     search_fields = ('name', 'slug', 'external_id', 'registration_number', 'notes', 'website')
#     list_editable = ('status',)
#     date_hierarchy = 'created_at'
#     ordering = ('name',)
#     list_select_related = True
#     list_per_page = 50
#     select_related_fields = ['industry', 'default_address__city__subregion__region__country', 'parent', 'created_by', 'updated_by', 'deleted_by']
#     prefetch_related_fields = ['children']
#     mptt_level_indent = 20
#     mptt_indent_field = 'name'
#     autocomplete_fields = ['default_address', 'industry', 'parent']
#     actions = ['soft_delete', 'restore']
#     list_display_links = ('name',)
#     ordering = ('-id',)

#     base_fieldsets_config = [
#         (None, {
#             'fields': ('name', 'slug', 'entity_type', 'status', 'website')
#         }),
#         (_('Details'), {
#             'fields': ('registration_number', 'entity_size', 'industry', 'default_address', 'parent', 'notes')
#         }),
#     ]

#     def get_fieldset_conditions(self, request, obj=None):
#         return []

#     @admin.display(description='Name')
#     def name_display(self, obj):
#         url = reverse('admin:entities_entity_change', args=[obj.pk])
#         return format_html(
#             '<div style="text-align: left;"><a href="{}">{}</a></div>',
#             url,
#             obj.name
#         )

#     def headquarter_location(self, obj):
#         return obj.get_headquarter_location()
#     headquarter_location.short_description = 'Headquarter'

#     def country(self, obj):
#         return obj.get_country()
#     country.short_description = 'Country'

#     @admin.display(description='Industry')
#     def industry_display(self, obj):
#         return obj.industry.description if obj.industry else '-'

#     @admin.display(description='Parent Entity')
#     def parent_entity_display(self, obj):
#         if obj.parent:
#             url = reverse('admin:entities_entity_change', args=[obj.parent.pk])
#             return format_html('<a href="{}">{}</a>', url, obj.parent.name)
#         return '-'

#     @admin.display(description='Ext ID')
#     def display_ext_id(self, obj):
#         return obj.external_id if obj.external_id else '-'

#     def get_readonly_fields(self, request, obj=None):
#         readonly = super().get_readonly_fields(request, obj)
#         return readonly

#     def get_form(self, request, obj=None, **kwargs):
#         form = super().get_form(request, obj, **kwargs)
#         if 'default_address' in form.base_fields:
#             form.base_fields['default_address'].label_from_instance = lambda obj: (
#                 f"{obj.get_full_address()}" if obj.entity_mapping and obj.entity_mapping.entity_type == 'entities.Entity'
#                 else '-'
#             )
#         return form


#     def changelist_view(self, request, extra_context=None):
#         extra_context = extra_context or {}
#         return super().changelist_view(request, extra_context)

#     def get_model_perms(self, request):
#         perms = super().get_model_perms(request)
#         perms['index'] = True
#         return perms

