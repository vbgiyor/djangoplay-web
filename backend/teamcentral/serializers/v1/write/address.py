from teamcentral.serializers.base import BaseAddressSerializer


class AddressWriteSerializerV1(BaseAddressSerializer):
    class Meta(BaseAddressSerializer.Meta):
        fields = (
            "address",
            "address_type",
            "country",
            "state",
            "city",
            "postal_code",
            "emergency_contact",
            "is_active",
        )
