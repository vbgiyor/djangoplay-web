from locations.serializers.base import BaseLocationSerializer


class LocationReadSerializerV1(BaseLocationSerializer):
    class Meta(BaseLocationSerializer.Meta):
        fields = BaseLocationSerializer.Meta.fields + (
            "created_at",
            "updated_at",
        )
