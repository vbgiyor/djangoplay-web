import logging
from decimal import Decimal

from core.admin_mixins import AdminIconDecorator, BaseAdmin
from django.contrib import admin
from django.contrib.admin import SimpleListFilter, TabularInline
from django.db import transaction
from django.db.models import Prefetch
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from locations.models import CustomRegion
from users.utils.helpers import user_is_verified_employee
from utilities.admin.admin_filters import *
from utilities.signals.disable_signals import disable_signals

from invoices.forms import (
    BillingScheduleForm,
    GSTConfigurationForm,
    InvoiceForm,
    LineItemForm,
    PaymentForm,
    PaymentMethodForm,
    StatusForm,
)
from invoices.models.billing_schedule import BillingSchedule
from invoices.models.gst_configuration import GSTConfiguration
from invoices.models.invoice import Invoice
from invoices.models.line_item import LineItem
from invoices.models.payment import Payment
from invoices.models.payment_method import PaymentMethod
from invoices.models.status import Status

logger = logging.getLogger(__name__)

class ChangelistLinkMixin:
    def changelist_link(self, obj):
        url = reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_changelist')
        return format_html('<a href="{}">View All {}</a>', url, obj._meta.verbose_name_plural.title())

    changelist_link.short_description = 'Changelist'

    def get_list_display(self, request):
        return super().get_list_display(request) + ('changelist_link',)

class PaymentInline(TabularInline):
    model = Payment
    extra = 0
    fields = ('payment_method', 'payment_reference', 'amount', 'payment_date', 'status')
    readonly_fields = ('amount', 'payment_date', 'status')
    autocomplete_fields = ['payment_method']
    can_delete = True
    show_change_link = True


@AdminIconDecorator.register_with_icon(LineItem)
class LineItemAdmin(BaseAdmin):
    form = LineItemForm
    list_display = (
        'id', 'invoice_display', 'description', 'quantity',
        'unit_price', 'discount', 'total_amount', 'is_active'
    )
    search_fields = ('description', 'hsn_sac_code', 'invoice__invoice_number')
    list_per_page = 50
    autocomplete_fields = ['invoice']
    ordering = ('-invoice__issue_date', '-id')
    actions = ['soft_delete', 'restore']
    list_display_links = ('description',)

    select_related_fields = [
        'invoice__billing_country', 'created_by', 'updated_by', 'deleted_by'
    ]
    prefetch_related_fields = [
        Prefetch('invoice__status', queryset=Status.objects.filter(is_active=True)),
    ]

    base_fieldsets_config = [
        (_('Details'), {
            'fields': ('invoice', 'description', 'quantity', 'unit_price', 'discount')
        }),
        (_('Tax Rates'), {
            'fields': ('cgst_rate', 'sgst_rate', 'igst_rate')
        }),
        (_('Tax Amounts'), {
            'fields': ('cgst_amount', 'sgst_amount', 'igst_amount')
        }),
        (_('Total'), {
            'fields': ('total_amount',)
        }),
    ]

    conditional_fieldsets = {
        'india': (_('India Specific'), {
            'fields': ('hsn_sac_code',)
        })
    }

    def get_fieldset_conditions(self, request, obj=None):
        conditions = []
        if obj and obj.invoice and obj.invoice.billing_country:
            country_code = getattr(obj.invoice.billing_country, 'country_code', '').upper()
            if country_code == 'IN':
                conditions.append('india')
        return conditions

    @admin.display(description='Invoice')
    def invoice_display(self, obj):
        if obj.invoice:
            url = reverse('admin:invoices_invoice_change', args=[obj.invoice.pk])
            return format_html('<a href="{}">{}</a>', url, obj.invoice.invoice_number)
        return '-'

    def get_list_display(self, request):
        list_display = list(self.list_display)
        country_code = request.GET.get('country_filter')
        if country_code and country_code.upper() == 'IN' and 'hsn_sac_code' not in list_display:
            list_display.insert(2, 'hsn_sac_code')
        elif 'hsn_sac_code' in list_display and (not country_code or country_code.upper() != 'IN'):
            list_display.remove('hsn_sac_code')
        return list_display

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if 'invoice__search' in request.GET:
            queryset = queryset.filter(invoice__invoice_number__icontains=search_term)
        return queryset, use_distinct

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        readonly += [
            'cgst_rate', 'sgst_rate', 'igst_rate',
            'cgst_amount', 'sgst_amount', 'igst_amount',
            'total_amount'
        ]
        return readonly

    def get_list_filter(self, request):
        base_filters = [
            IsActiveFilter,
            changelist_filter("invoice"),
            changelist_filter("description"),
        ]
        return base_filters


@AdminIconDecorator.register_with_icon(Invoice)
class InvoiceAdmin(BaseAdmin):
    form = InvoiceForm
    list_display = (
        'invoice_number', 'issuer_display', 'recipient_display',
        'billing_country_display', 'status_display', 'total_amount',
        'issue_date', 'is_active'
    )
    search_fields = ('invoice_number', 'description', 'issuer__name', 'recipient__name')
    date_hierarchy = 'issue_date'
    # ordering = ('-issue_date', '-id')
    list_per_page = 50
    select_related_fields = [
        'issuer', 'recipient', 'billing_address',
        'billing_country', 'billing_region', 'status'
    ]
    prefetch_related_fields = [
        Prefetch(
            'line_items',
            queryset=LineItem.objects.filter(deleted_at__isnull=True)
                .only('id', 'description', 'total_amount')
        ),
        Prefetch(
            'payments',
            queryset=Payment.objects.filter(is_active=True)
                .only('id', 'amount', 'payment_reference'),
            to_attr='active_payments'
        )
    ]
    autocomplete_fields = [
        'issuer', 'recipient', 'billing_address',
        'billing_country', 'billing_region'
    ]
    actions = ['soft_delete', 'restore']
    list_display_links = ('invoice_number',)

    base_fieldsets_config = [
        (None, {
            'fields': ('invoice_number', 'description', 'status', 'payment_terms', 'tax_exemption_status')
        }),
        (_('Parties'), {
            'fields': ('issuer', 'recipient', 'billing_address', 'billing_country', 'billing_region')
        }),
        (_('Financial Details'), {
            'fields': ('currency', 'base_amount', 'cgst_rate', 'sgst_rate', 'igst_rate', 'total_amount')
        }),
        (_('Dates'), {
            'fields': ('issue_date', 'due_date')
        }),
    ]

    conditional_fieldsets = {
        'india': (_('Tax Details'), {
            'fields': ('issuer_gstin', 'recipient_gstin')
        })
    }

    def get_fieldset_conditions(self, request, obj=None):
        conditions = []
        if obj and obj.billing_country:
            country_code = getattr(obj.billing_country, 'country_code', '').upper()
            if country_code == 'IN':
                conditions.append('india')
        return conditions

    def get_inlines(self, request, obj=None):
        if obj and hasattr(obj, 'active_payments') and obj.active_payments:
            return [PaymentInline]
        return []

    @admin.display(description='Issuer')
    def issuer_display(self, obj):
        if obj.issuer:
            url = reverse('admin:entities_entity_change', args=[obj.issuer.pk])
            return format_html('<a href="{}">{}</a>', url, obj.issuer.name)
        return '-'

    @admin.display(description='Recipient')
    def recipient_display(self, obj):
        if obj.recipient:
            url = reverse('admin:entities_entity_change', args=[obj.recipient.pk])
            return format_html('<a href="{}">{}</a>', url, obj.recipient.name)
        return '-'

    @admin.display(description='Billing Country')
    def billing_country_display(self, obj):
        return obj.billing_country.name if obj.billing_country else '-'

    @admin.display(description='Invoice Status')
    def status_display(self, obj):
        return obj.status.name if obj.status and obj.status.is_active else f"Invalid ({obj.status_id})"

    @admin.display(description='Issuer GSTIN')
    def issuer_gstin_display(self, obj):
        return obj.issuer_gstin if obj.issuer_gstin else '-'

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        readonly += ['total_amount', 'status']
        return readonly

    def get_form(self, request, obj=None, **kwargs):
        with disable_signals(Invoice, LineItem, Payment):
            return super().get_form(request, obj, **kwargs)

    # def change_view(self, request, object_id, form_url='', extra_context=None):
    #     obj = self.get_object(request, object_id)
    #     return super().change_view(request, object_id, form_url, extra_context)

    # def get_actions(self, request):
    #     actions = super().get_actions(request)
    #     if 'delete_selected' in actions:
    #         del actions['delete_selected']
    #     return actions

    def save_model(self, request, obj, form, change):
        """Save the Invoice and update associated LineItems with new GST rates."""
        with transaction.atomic():
            obj.save(user=request.user, skip_validation=False)
            from invoices.services.line_item import calculate_line_item_total
            line_items = obj.line_items.filter(deleted_at__isnull=True)
            for line_item in line_items:
                line_item.cgst_rate = form.cleaned_data.get('cgst_rate', Decimal('0.00')).quantize(Decimal('0.01'))
                line_item.sgst_rate = form.cleaned_data.get('sgst_rate', Decimal('0.00')).quantize(Decimal('0.01'))
                line_item.igst_rate = form.cleaned_data.get('igst_rate', Decimal('0.00')).quantize(Decimal('0.01'))
                total_data = calculate_line_item_total(line_item)
                line_item.cgst_amount = total_data.get('cgst_amount', Decimal('0.00')).quantize(Decimal('0.01'))
                line_item.sgst_amount = total_data.get('sgst_amount', Decimal('0.00')).quantize(Decimal('0.01'))
                line_item.igst_amount = total_data.get('igst_amount', Decimal('0.00')).quantize(Decimal('0.01'))
                line_item.total_amount = total_data['total'].quantize(Decimal('0.01'))
                line_item.save(user=request.user, skip_validation=True)
        super().save_model(request, obj, form, change)


    def get_list_filter(self, request):
        base_filters = [IsActiveFilter]

        if user_is_verified_employee(request):
            base_filters.insert(0, CountryFilter)

        return base_filters

@AdminIconDecorator.register_with_icon(BillingSchedule)
class BillingScheduleAdmin(BaseAdmin):
    form = BillingScheduleForm
    list_display = ('entity_display', 'description', 'frequency', 'amount', 'start_date', 'next_billing_date', 'is_active')
    list_filter = ('frequency',)
    search_fields = ('description', 'entity__name')
    readonly_fields = ('status',)
    date_hierarchy = 'next_billing_date'
    ordering = ('-id', '-next_billing_date', )
    list_per_page = 50
    select_related_fields = ['entity', 'created_by', 'updated_by', 'deleted_by']
    autocomplete_fields = ['entity']
    actions = ['soft_delete', 'restore']
    list_display_links = ('description',)

    base_fieldsets_config = [
        (None, {
            'fields': ('entity', 'description', 'frequency', 'status')
        }),
        (_('Schedule Details'), {
            'fields': ('start_date', 'end_date', 'next_billing_date', 'amount')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    @admin.display(description='Entity')
    def entity_display(self, obj):
        if obj.entity:
            url = reverse('admin:entities_entity_change', args=[obj.entity.pk])
            return format_html('<a href="{}">{}</a>', url, obj.entity.name)
        return '-'

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


@AdminIconDecorator.register_with_icon(Payment)
class PaymentAdmin(BaseAdmin):
    icon = 'fa-solid fa-indian-rupee-sign'
    form = PaymentForm
    list_display = ('invoice_display', 'currency_display', 'amount', 'payment_date', 'payment_method_display', 'status', 'is_active')
    list_filter = ('status', 'payment_method')
    search_fields = ('invoice__invoice_number', 'payment_reference')
    date_hierarchy = 'payment_date'
    ordering = ('-id', '-payment_date',)
    list_per_page = 50
    select_related_fields = ['invoice', 'payment_method', 'created_by', 'updated_by', 'deleted_by']
    autocomplete_fields = ['invoice', 'payment_method']
    actions = ['soft_delete', 'restore']
    list_display_links = ('id',)

    base_fieldsets_config = [
        (None, {
            'fields': ('invoice', 'amount', 'status')
        }),
        (_('Payment Details'), {
            'fields': ('payment_date', 'payment_method', 'payment_reference')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    @admin.display(description='Invoice')
    def invoice_display(self, obj):
        if obj.invoice:
            url = reverse('admin:invoices_invoice_change', args=[obj.invoice.pk])
            return format_html('<a href="{}">{}</a>', url, obj.invoice.invoice_number)
        return '-'

    @admin.display(description='Currency')
    def currency_display(self, obj):
        # Access the currency from the related Invoice
        if obj.invoice and obj.invoice.currency:
            return obj.invoice.currency
        return '-'

    @admin.display(description='Payment Method')
    def payment_method_display(self, obj):
        return obj.payment_method.name if obj.payment_method else '-'

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


@AdminIconDecorator.register_with_icon(PaymentMethod)
class PaymentMethodAdmin(BaseAdmin):
    icon = 'fas fa-credit-card'
    form = PaymentMethodForm
    list_display = ('code', 'name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('code', 'name', 'description')
    list_editable = ('is_active',)
    list_per_page = 50
    select_related_fields = ['created_by', 'updated_by', 'deleted_by']
    actions = ['soft_delete', 'restore']
    list_display_links = ('code',)

    base_fieldsets_config = [
        (None, {
            'fields': ('code', 'name', 'is_active')
        }),
        (_('Details'), {
            'fields': ('description',)
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


@AdminIconDecorator.register_with_icon(Status)
class StatusAdmin(BaseAdmin):
    icon = 'fas fa-clipboard-check'
    form = StatusForm
    list_display = ('name', 'code', 'is_default', 'is_locked', 'is_active')
    list_filter = ('is_default', 'is_locked', 'is_active')
    search_fields = ('name', 'code')
    list_editable = ('is_default', 'is_locked')
    list_per_page = 50
    select_related_fields = ['created_by', 'updated_by', 'deleted_by']
    actions = ['soft_delete', 'restore']
    list_display_links = ('name',)

    base_fieldsets_config = [
        (None, {
            'fields': ('name', 'code', 'is_default', 'is_locked')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

class ApplicableRegionFilter(SimpleListFilter):
    title = 'Applicable Region (India)'
    parameter_name = 'applicable_region'

    def lookups(self, request, model_admin):
        regions = CustomRegion.objects.filter(
            country__country_code='IN',
            deleted_at__isnull=True,
            is_active=True
        ).select_related('country').order_by('name')
        return [(region.id, region.name) for region in regions]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(applicable_region_id=self.value())
        return queryset

@AdminIconDecorator.register_with_icon(GSTConfiguration)
class GSTConfigurationAdmin(BaseAdmin):
    icon = 'fas fa-receipt'
    form = GSTConfigurationForm
    list_display = ('description', 'cgst_rate', 'sgst_rate', 'igst_rate', 'rate_type', 'is_active')
    list_filter = ('rate_type', ApplicableRegionFilter)
    search_fields = ('description',)
    list_per_page = 50
    select_related_fields = ['applicable_region', 'created_by', 'updated_by', 'deleted_by']
    autocomplete_fields = ['applicable_region']
    actions = ['soft_delete', 'restore']
    list_display_links = ('description',)
    ordering = ('-id',)

    base_fieldsets_config = [
        (None, {
            'fields': ('description', 'rate_type')
        }),
        (_('Tax Rates'), {
            'fields': ('cgst_rate', 'sgst_rate', 'igst_rate')
        }),
        (_('Tax Amounts'), {
            'fields': ('cgst_amount', 'sgst_amount', 'igst_amount')
        }),
        (_('Validity'), {
            'fields': ('applicable_region', 'effective_from', 'effective_to')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        readonly += ('cgst_amount', 'sgst_amount', 'igst_amount')
        return readonly

    def get_form(self, request, obj=None, **kwargs):
        logger.debug(f"Initializing GSTConfigurationForm for obj={obj}, fields={GSTConfigurationForm.Meta.fields}")
        with disable_signals(GSTConfiguration):
            return super().get_form(request, obj, **kwargs)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
