from rest_framework import serializers

from locations.models import GlobalRegion


class BaseGlobalRegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalRegion
        fields = (
            "id",
            "name",
            "code",
            "is_active",
        )
        read_only_fields = ("id",)
