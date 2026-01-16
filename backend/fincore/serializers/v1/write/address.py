from fincore.serializers.base.address import BaseAddressSerializer


class FincoreAddressWriteSerializerV1(BaseAddressSerializer):
    class Meta(BaseAddressSerializer.Meta):
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "deleted_at",
            "deleted_by",
        )
