from clients.models import Client
from clients.serializers import ClientInvoicePurposeSerializer
from django.utils import timezone
from rest_framework import serializers

from .models import Invoice, InvoiceStatus, PaymentMethod


class InvoiceBaseSerializer(serializers.ModelSerializer):

    """Base serializer for Invoice model with common fields and validation."""

    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        source='client'
    )
    status = serializers.PrimaryKeyRelatedField(
        queryset=InvoiceStatus.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )
    payment_method = serializers.PrimaryKeyRelatedField(
        queryset=PaymentMethod.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Invoice
        fields = [
            'id',
            'client_id',
            'invoice_number',
            'issue_date',
            'due_date',
            'amount',
            'status',
            'payment_method',
            'payment_reference',
            'notes',
            'docs',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'invoice_number', 'created_at', 'updated_at']


class InvoiceReadSerializer(InvoiceBaseSerializer):

    """Serializer for reading Invoice data with additional display fields."""

    client = ClientInvoicePurposeSerializer(read_only=True)
    status_display = serializers.CharField(
        source='status.name', read_only=True)  # Human-readable status name
    payment_method_display = serializers.CharField(
        source='payment_method.name', read_only=True)  # Human-readable payment method
    docs_url = serializers.SerializerMethodField()  # URL for invoice documents
    is_overdue = serializers.SerializerMethodField()  # Indicates if invoice is overdue

    class Meta(InvoiceBaseSerializer.Meta):
        fields = InvoiceBaseSerializer.Meta.fields + [
            'client',
            'status_display',
            'payment_method_display',
            'docs_url',
            'is_overdue',
        ]

    def get_docs_url(self, obj):
        """Return absolute URL for invoice documents if available."""
        if obj.docs:
            request = self.context.get('request')
            return request.build_absolute_uri(
                obj.docs.url) if request else obj.docs.url
        return None

    def get_is_overdue(self, obj):
        """Check if invoice is overdue based on due date and status."""
        if obj.status and obj.due_date and obj.status.code not in [
                'paid', 'cancelled']:
            return obj.due_date < timezone.now().date()
        return False


class InvoiceWriteSerializer(InvoiceBaseSerializer):

    """Serializer for writing Invoice data with due date validation."""

    def validate_due_date(self, value):
        """Ensure due date is not earlier than issue date."""
        issue_date = self.initial_data.get('issue_date')
        if issue_date:
            try:
                issue_date = timezone.datetime.strptime(
                    issue_date, '%Y-%m-%d').date()
            except ValueError as err:
                raise serializers.ValidationError(
                    "Invalid issue date format. Use YYYY-MM-DD.") from err
        else:
            issue_date = timezone.now().date()

        if value < issue_date:
            raise serializers.ValidationError(
                "Due date cannot be earlier than issue date.")
        return value
