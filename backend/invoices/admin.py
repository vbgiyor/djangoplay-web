from django.contrib import admin
from django.utils import timezone

from .models import Invoice, InvoicePayment, InvoiceStatus, PaymentMethod


@admin.register(InvoiceStatus)
class InvoiceStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_default', 'is_active')
    list_filter = ('is_active', 'is_default')
    search_fields = ('name', 'code')


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')


class InvoicePaymentInline(admin.TabularInline):
    model = InvoicePayment
    extra = 1
    readonly_fields = ('paid_at',)
    autocomplete_fields = ('method',)  # Optional: Improves performance if large number of methods

    def paid_at(self, obj):
        """Format paid_at with AM/PM and hh:mm:ss."""
        if obj.paid_at:
            return obj.paid_at.strftime('%B %d, %Y, %I:%M:%S %p')
        return "-"
    paid_at.short_description = "Paid At"


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
    )
    list_filter = ('status', 'payment_method', 'issue_date', 'due_date')
    search_fields = ('invoice_number', 'client__name', 'notes')
    readonly_fields = ('invoice_number', 'created_at', 'updated_at')
    autocomplete_fields = ('client', 'status', 'payment_method')
    inlines = [InvoicePaymentInline]

    def get_queryset(self, request):
        """Use select_related to reduce queries."""
        qs = super().get_queryset(request)
        return qs.select_related('client', 'status', 'payment_method')

    def is_overdue(self, obj):
        if not obj.status or obj.status.code not in ['paid', 'cancelled']:
            return obj.due_date < timezone.now().date()
        return False
    is_overdue.boolean = True
    is_overdue.short_description = 'Overdue'


@admin.register(InvoicePayment)
class InvoicePaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'amount', 'method', 'paid_at', 'reference')
    list_filter = ('method', 'paid_at')
    search_fields = ('invoice__invoice_number', 'reference')
    autocomplete_fields = ('invoice', 'method')
