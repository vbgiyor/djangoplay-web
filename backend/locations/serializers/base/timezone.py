from rest_framework import serializers

from locations.models import Timezone


class BaseTimezoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timezone
        fields = (
            "id",
            "timezone_id",
            "raw_offset",
            "is_active",
        )
        read_only_fields = ("id",)
