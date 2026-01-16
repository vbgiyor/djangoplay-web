from rest_framework import serializers

from invoices.models.payment_method import PaymentMethod


class PaymentMethodReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ("id", "code", "name", "description", "is_active")
        read_only_fields = fields
