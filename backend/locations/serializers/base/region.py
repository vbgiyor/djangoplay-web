from rest_framework import serializers

from locations.models import CustomRegion


class BaseRegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomRegion
        fields = (
            "id",
            "name",
            "code",
            "country",
            "is_active",
        )
        read_only_fields = ("id",)
