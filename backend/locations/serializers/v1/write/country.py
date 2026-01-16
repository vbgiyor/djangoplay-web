from locations.serializers.base.country import BaseCountrySerializer


class CountryWriteSerializerV1(BaseCountrySerializer):
    class Meta(BaseCountrySerializer.Meta):
        fields = (
            "name",
            "country_code",
            "currency_code",
            "population",
            "is_active",
        )
