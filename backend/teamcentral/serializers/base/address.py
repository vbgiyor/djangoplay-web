from rest_framework import serializers

from teamcentral.models import Address


class BaseAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = (
            "id",
            "address",
            "address_type",
            "country",
            "state",
            "city",
            "postal_code",
            "emergency_contact",
            "is_active",
        )
        read_only_fields = ("id",)
