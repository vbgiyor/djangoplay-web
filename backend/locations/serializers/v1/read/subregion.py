from locations.serializers.base import BaseSubRegionSerializer


class SubRegionReadSerializerV1(BaseSubRegionSerializer):
    class Meta(BaseSubRegionSerializer.Meta):
        fields = BaseSubRegionSerializer.Meta.fields + (
            "created_at",
            "updated_at",
        )
