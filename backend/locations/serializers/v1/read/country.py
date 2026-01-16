from locations.serializers.base import BaseCountrySerializer


class CountryReadSerializerV1(BaseCountrySerializer):
    class Meta(BaseCountrySerializer.Meta):
        fields = BaseCountrySerializer.Meta.fields + (
            "created_at",
            "updated_at",
        )
