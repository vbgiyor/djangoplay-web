from fincore.models import Address
from rest_framework import serializers


class FincoreAddressReadSerializerV1(serializers.ModelSerializer):
    full_address = serializers.CharField(source="get_full_address", read_only=True)

    class Meta:
        model = Address
        fields = (
            "id",
            "entity_mapping",
            "address_type",
            "street_address",
            "city",
            "region",
            "subregion",
            "country",
            "postal_code",
            "is_default",
            "full_address",
            "created_at",
            "updated_at",
        )
