from rest_framework import serializers

from teamcentral.models import Team


class BaseTeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = (
            "id",
            "name",
            "department",
            "leader",
            "description",
            "is_active",
        )
        read_only_fields = ("id",)
