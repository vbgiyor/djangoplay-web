from clients.models import Client
from clients.serializers import ClientInvoicePurposeSerializer
from django.utils import timezone
from rest_framework import serializers

from .models import Invoice, InvoiceStatus, PaymentMethod


class InvoiceBaseSerializer(serializers.ModelSerializer):
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
            'pdf',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'invoice_number', 'created_at', 'updated_at']


class InvoiceReadSerializer(InvoiceBaseSerializer):
    client = ClientInvoicePurposeSerializer(read_only=True)
    status_display = serializers.CharField(source='status.name', read_only=True)
    payment_method_display = serializers.CharField(source='payment_method.name', read_only=True)
    pdf_url = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta(InvoiceBaseSerializer.Meta):
        fields = InvoiceBaseSerializer.Meta.fields + [
            'client',
            'status_display',
            'payment_method_display',
            'pdf_url',
            'is_overdue',
        ]

    def get_pdf_url(self, obj):
        if obj.pdf:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.pdf.url) if request else obj.pdf.url
        return None

    def get_is_overdue(self, obj):
        if obj.status and obj.due_date and obj.status.code not in ['paid', 'cancelled']:
            return obj.due_date < timezone.now().date()
        return False


class InvoiceWriteSerializer(InvoiceBaseSerializer):
    def validate_due_date(self, value):
        issue_date = self.initial_data.get('issue_date')
        if issue_date:
            try:
                issue_date = timezone.datetime.strptime(issue_date, '%Y-%m-%d').date()
            except ValueError:
                raise serializers.ValidationError("Invalid issue date format. Use YYYY-MM-DD.")
        else:
            issue_date = timezone.now().date()

        if value < issue_date:
            raise serializers.ValidationError("Due date cannot be earlier than issue date.")
        return value
