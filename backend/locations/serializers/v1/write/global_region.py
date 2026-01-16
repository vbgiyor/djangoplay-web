from locations.serializers.base import BaseGlobalRegionSerializer


class GlobalRegionWriteSerializerV1(BaseGlobalRegionSerializer):
    class Meta(BaseGlobalRegionSerializer.Meta):
        fields = (
            "name",
            "code",
            "is_active",
        )
