from django.contrib import admin
from django.db import models
from django.utils import timezone

from .models import Invoice, InvoicePayment, InvoiceStatus, PaymentMethod


@admin.register(InvoiceStatus)
class InvoiceStatusAdmin(admin.ModelAdmin):

    """Admin for InvoiceStatus model."""

    list_display = ('name', 'code', 'is_default', 'is_active')
    list_filter = ('is_active', 'is_default')
    search_fields = ('name', 'code')
    readonly_fields = ('code',)
    fields = ('name', 'code', 'description', 'is_default', 'is_active')


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):

    """Admin for PaymentMethod model."""

    list_display = ('name', 'code', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    readonly_fields = ('code',)
    fields = ('name', 'code', 'description', 'is_active')


class InvoicePaymentInline(admin.TabularInline):

    """Inline admin for InvoicePayment model."""

    model = InvoicePayment
    extra = 0
    readonly_fields = ('reference', 'paid_at', 'created_at', 'updated_at')
    fields = ('method', 'amount', 'reference', 'paid_at')
    autocomplete_fields = ('method',)

    def paid_at(self, obj):
        """Format paid_at date."""
        return obj.paid_at.strftime('%B %d, %Y, %I:%M:%S %p') if obj.paid_at else "-"
    paid_at.short_description = "Paid At"


class OverdueFilter(admin.SimpleListFilter):

    """Filter for overdue invoices."""

    title = 'Overdue'
    parameter_name = 'is_overdue'

    def lookups(self, request, model_admin):
        return (('yes', 'Overdue'), ('no', 'Not Overdue'))

    def queryset(self, request, queryset):
        """Filter invoices based on overdue status."""
        queryset = queryset.annotate(
            total_paid=models.Sum(
                'payments__amount',
                filter=models.Q(payments__deleted_at__isnull=True),
                default=0
            )
        )
        if self.value() == 'yes':
            return queryset.filter(
                deleted_at__isnull=True,
                due_date__lt=timezone.now().date(),
                amount__gt=models.F('total_paid')
            ).exclude(status__code__in=['paid', 'cancelled'])
        if self.value() == 'no':
            return queryset.filter(
                models.Q(deleted_at__isnull=False) |
                models.Q(due_date__gte=timezone.now().date()) |
                models.Q(amount__lte=models.F('total_paid'))
            ).exclude(status__code__in=['paid', 'cancelled'])
        return queryset


class DeletedFilter(admin.SimpleListFilter):

    """Filter for soft-deleted records."""

    title = 'Deleted'
    parameter_name = 'is_deleted'

    def lookups(self, request, model_admin):
        return (('yes', 'Deleted'), ('no', 'Not Deleted'))

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(deleted_at__isnull=False)
        if self.value() == 'no':
            return queryset.filter(deleted_at__isnull=True)
        return queryset


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):

    """Admin for Invoice model."""

    list_display = (
        'invoice_number', 'client', 'amount', 'status', 'payment_method',
        'issue_date', 'due_date', 'is_overdue', 'remaining_amount', 'deleted_at'
    )
    list_filter = ('status', 'payment_method', 'issue_date', 'due_date', OverdueFilter, DeletedFilter)
    search_fields = ('invoice_number', 'client__name', 'notes')
    readonly_fields = ('invoice_number', 'created_at', 'updated_at', 'deleted_at')
    fields = ('client', 'issue_date', 'due_date', 'amount', 'status', 'payment_method', 'notes', 'docs')
    autocomplete_fields = ('client', 'status', 'payment_method')
    inlines = [InvoicePaymentInline]
    ordering = ['-issue_date']
    actions = ['restore_selected']

    def get_inlines(self, request, obj):
        """Show inline only for existing invoices."""
        return [InvoicePaymentInline] if obj else []

    def get_queryset(self, request):
        """Include soft-deleted invoices for admin."""
        return super().get_queryset(request).select_related('client', 'status', 'payment_method')

    def is_overdue(self, obj):
        """Display overdue status."""
        return obj.is_overdue
    is_overdue.boolean = True
    is_overdue.short_description = 'Overdue'

    def remaining_amount(self, obj):
        """Display remaining amount."""
        return obj.remaining_amount
    remaining_amount.short_description = 'Remaining Amount'

    def delete_model(self, request, obj):
        """Soft delete single invoice."""
        obj.soft_delete()

    def delete_queryset(self, request, queryset):
        """Soft delete multiple invoices."""
        queryset.update(deleted_at=timezone.now())

    def restore_selected(self, request, queryset):
        """Restore selected soft-deleted invoices."""
        restored_count = queryset.filter(deleted_at__isnull=False).update(deleted_at=None)
        self.message_user(request, f"Restored {restored_count} invoice(s).")
    restore_selected.short_description = "Restore selected invoices"


@admin.register(InvoicePayment)
class InvoicePaymentAdmin(admin.ModelAdmin):

    """Admin for InvoicePayment model."""

    list_display = ('invoice', 'amount', 'method', 'paid_at', 'reference', 'deleted_at')
    list_filter = ('method', 'paid_at', DeletedFilter)
    search_fields = ('invoice__invoice_number', 'reference')
    readonly_fields = ('reference', 'paid_at', 'created_at', 'updated_at', 'deleted_at')
    fields = ('invoice', 'method', 'amount')
    autocomplete_fields = ('invoice', 'method')
    ordering = ['-paid_at']
    actions = ['restore_selected']

    def get_queryset(self, request):
        """Include soft-deleted payments for admin."""
        return super().get_queryset(request).select_related('invoice', 'method')

    def restore_selected(self, request, queryset):
        """Restore selected soft-deleted payments."""
        restored_count = queryset.filter(deleted_at__isnull=False).update(deleted_at=None)
        self.message_user(request, f"Restored {restored_count} payment(s).")
    restore_selected.short_description = "Restore selected payments"
