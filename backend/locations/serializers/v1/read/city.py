from locations.serializers.base import BaseCitySerializer


class CityReadSerializerV1(BaseCitySerializer):
    class Meta(BaseCitySerializer.Meta):
        fields = BaseCitySerializer.Meta.fields + (
            "created_at",
            "updated_at",
        )
