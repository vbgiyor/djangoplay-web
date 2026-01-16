from rest_framework import serializers

from invoices.models.status import Status


class StatusReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ("id", "name", "code", "is_default", "is_locked")
        read_only_fields = fields
