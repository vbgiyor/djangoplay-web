from locations.serializers.base import BaseCitySerializer


class CityWriteSerializerV1(BaseCitySerializer):
    class Meta(BaseCitySerializer.Meta):
        fields = (
            "name",
            "code",
            "subregion",
            "timezone",
            "latitude",
            "longitude",
            "is_active",
        )
