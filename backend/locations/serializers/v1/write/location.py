from locations.serializers.base import BaseLocationSerializer


class LocationWriteSerializerV1(BaseLocationSerializer):
    class Meta(BaseLocationSerializer.Meta):
        fields = (
            "city",
            "postal_code",
            "latitude",
            "longitude",
            "is_active",
        )
