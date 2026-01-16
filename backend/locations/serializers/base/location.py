from rest_framework import serializers

from locations.models import Location


class BaseLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = (
            "id",
            "city",
            "postal_code",
            "latitude",
            "longitude",
            "is_active",
        )
        read_only_fields = ("id",)
