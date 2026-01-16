from locations.serializers.base import BaseTimezoneSerializer


class TimezoneReadSerializerV1(BaseTimezoneSerializer):
    class Meta(BaseTimezoneSerializer.Meta):
        fields = BaseTimezoneSerializer.Meta.fields + (
            "created_at",
            "updated_at",
        )
