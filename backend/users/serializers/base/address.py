from rest_framework import serializers

from users.models.address import Address


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
            "address_type",
            "emergency_contact",
            "is_active",
        )
        read_only_fields = ("id",)
