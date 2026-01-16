from locations.serializers.base import BaseSubRegionSerializer


class SubRegionWriteSerializerV1(BaseSubRegionSerializer):
    class Meta(BaseSubRegionSerializer.Meta):
        fields = (
            "name",
            "code",
            "region",
            "is_active",
        )
