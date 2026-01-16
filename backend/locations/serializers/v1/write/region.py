from locations.serializers.base import BaseRegionSerializer


class RegionWriteSerializerV1(BaseRegionSerializer):
    class Meta(BaseRegionSerializer.Meta):
        fields = (
            "name",
            "code",
            "country",
            "is_active",
        )
