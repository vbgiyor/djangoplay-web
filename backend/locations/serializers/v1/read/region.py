from locations.serializers.base import BaseRegionSerializer


class RegionReadSerializerV1(BaseRegionSerializer):
    class Meta(BaseRegionSerializer.Meta):
        fields = BaseRegionSerializer.Meta.fields + (
            "created_at",
            "updated_at",
        )
