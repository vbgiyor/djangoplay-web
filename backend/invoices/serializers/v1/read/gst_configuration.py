from locations.models import CustomRegion
from rest_framework import serializers

from invoices.models.gst_configuration import GSTConfiguration


class GSTConfigRegionMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomRegion
        fields = ("id", "name", "code")
        read_only_fields = fields
        ref_name = "GSTConfigRegionReadMini"


class GSTConfigurationReadSerializer(serializers.ModelSerializer):
    applicable_region = GSTConfigRegionMiniSerializer(read_only=True)

    class Meta:
        model = GSTConfiguration
        fields = (
            "id",
            "description",
            "rate_type",
            "cgst_rate",
            "sgst_rate",
            "igst_rate",
            "applicable_region",
            "effective_from",
            "effective_to",
        )
        read_only_fields = fields

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        for f in ["cgst_rate", "sgst_rate", "igst_rate"]:
            if rep.get(f) is not None:
                rep[f] = str(rep[f])
        for d in ["effective_from", "effective_to"]:
            if rep.get(d):
                rep[d] = rep[d].isoformat()
        return rep
