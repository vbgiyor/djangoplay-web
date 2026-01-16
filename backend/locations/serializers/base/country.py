from rest_framework import serializers

from locations.models import CustomCountry


class BaseCountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomCountry
        fields = (
            "id",
            "name",
            "country_code",
            "currency_code",
            "global_regions",
            "is_active",
        )
        read_only_fields = ("id",)
