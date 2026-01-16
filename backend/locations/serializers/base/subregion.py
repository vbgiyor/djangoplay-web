from rest_framework import serializers

from locations.models import CustomSubRegion


class BaseSubRegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomSubRegion
        fields = (
            "id",
            "name",
            "code",
            "region",
            "is_active",
        )
        read_only_fields = ("id",)
