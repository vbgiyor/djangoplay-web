from locations.serializers.base import BaseTimezoneSerializer


class TimezoneWriteSerializerV1(BaseTimezoneSerializer):
    class Meta(BaseTimezoneSerializer.Meta):
        fields = (
            "timezone_id",
            "raw_offset",
            "is_active",
        )
