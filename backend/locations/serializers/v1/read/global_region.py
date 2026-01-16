from locations.serializers.base import BaseGlobalRegionSerializer


class GlobalRegionReadSerializerV1(BaseGlobalRegionSerializer):
    class Meta(BaseGlobalRegionSerializer.Meta):
        fields = BaseGlobalRegionSerializer.Meta.fields + (
            "created_at",
            "updated_at",
        )
