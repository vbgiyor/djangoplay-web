from users.serializers.base import BaseAddressSerializer


class AddressReadSerializerV1(BaseAddressSerializer):
    class Meta(BaseAddressSerializer.Meta):
        fields = BaseAddressSerializer.Meta.fields + (
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )
