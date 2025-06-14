from django.contrib import admin
from django.db import models
from django.utils import timezone

from .models import Invoice, InvoicePayment, InvoiceStatus, PaymentMethod


@admin.register(InvoiceStatus)
class InvoiceStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_default', 'is_active')
    list_filter = ('is_active', 'is_default')
    search_fields = ('name', 'code')
    readonly_fields = ('code',)
    fields = ('name', 'code', 'description', 'is_default', 'is_active')


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    readonly_fields = ('code',)
    fields = ('name', 'code', 'description', 'is_active')


class InvoicePaymentInline(admin.TabularInline):
    model = InvoicePayment
    extra = 0  # No extra forms by default
    readonly_fields = ('reference', 'paid_at', 'created_at', 'updated_at')
    fields = ('method', 'amount', 'reference', 'paid_at')
    autocomplete_fields = ('method',)

    def paid_at(self, obj):
        if obj.paid_at:
            return obj.paid_at.strftime('%B %d, %Y, %I:%M:%S %p')
        return "-"
    paid_at.short_description = "Paid At"


class OverdueFilter(admin.SimpleListFilter):
    title = 'Overdue'
    parameter_name = 'is_overdue'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Overdue'),
            ('no', 'Not Overdue'),
        )

    def queryset(self, request, queryset):
        # Annotate total paid amount for all active payments
        queryset = queryset.annotate(
            total_paid=models.Sum(
                'payments__amount',
                filter=models.Q(payments__deleted_at__isnull=True),
                default=0  # Ensures total_paid is 0 if no payments exist
            )
        )

        if self.value() == 'yes':
            return queryset.filter(
                deleted_at__isnull=True,  # Not deleted
                due_date__lt=timezone.now().date(),  # Past due date
                amount__gt=models.F('total_paid')  # Amount exceeds paid
            ).exclude(
                status__code__in=['paid', 'cancelled']  # Not paid or cancelled
            )

        if self.value() == 'no':
            return queryset.filter(
                models.Q(deleted_at__isnull=False) |  # Deleted
                models.Q(due_date__gte=timezone.now().date()) |  # Not yet due
                models.Q(amount__lte=models.F('total_paid'))  # Fully paid
            ).exclude(
                status__code__in=['paid', 'cancelled']  # Not paid or cancelled
            )

        return queryset


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_number',
        'client',
        'amount',
        'status',
        'payment_method',
        'issue_date',
        'due_date',
        'is_overdue',
        'remaining_amount',
    )
    list_filter = ('status', 'payment_method', 'issue_date', 'due_date', OverdueFilter)
    search_fields = ('invoice_number', 'client__name', 'notes')
    readonly_fields = ('invoice_number', 'created_at', 'updated_at', 'deleted_at')
    fields = (
        'client',
        'issue_date',
        'due_date',
        'amount',
        'status',
        'payment_method',
        'notes',
        'docs',
    )
    autocomplete_fields = ('client', 'status', 'payment_method')
    inlines = [InvoicePaymentInline]
    ordering = ['-issue_date']

    def get_inlines(self, request, obj):
        """Only show InvoicePaymentInline for existing invoices."""
        if obj is None:  # New invoice
            return []
        return [InvoicePaymentInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(deleted_at__isnull=True).select_related('client', 'status', 'payment_method')

    def is_overdue(self, obj):
        """Use the model's is_overdue property."""
        return obj.is_overdue
    is_overdue.boolean = True
    is_overdue.short_description = 'Overdue'

    def remaining_amount(self, obj):
        """Display the remaining amount in the admin list view."""
        return obj.remaining_amount
    remaining_amount.short_description = 'Remaining Amount'

    def delete_model(self, request, obj):
        obj.soft_delete()

    def delete_queryset(self, request, queryset):
        queryset.update(deleted_at=timezone.now())


@admin.register(InvoicePayment)
class InvoicePaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'amount', 'method', 'paid_at', 'reference')
    list_filter = ('method', 'paid_at')
    search_fields = ('invoice__invoice_number', 'reference')
    readonly_fields = ('reference', 'paid_at', 'created_at', 'updated_at')
    fields = ('invoice', 'method', 'amount')
    autocomplete_fields = ('invoice', 'method')
    ordering = ['-paid_at']

    def get_queryset(self, request):
        """Exclude soft-deleted payments."""
        qs = super().get_queryset(request)
        return qs.filter(invoice__deleted_at__isnull=True).select_related('invoice', 'method')
