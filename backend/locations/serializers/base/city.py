from rest_framework import serializers

from locations.models import CustomCity


class BaseCitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomCity
        fields = (
            "id",
            "name",
            "code",
            "subregion",
            "timezone",
            "latitude",
            "longitude",
            "is_active",
        )
        read_only_fields = ("id",)
