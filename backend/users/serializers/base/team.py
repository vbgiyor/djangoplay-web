from rest_framework import serializers

from users.models.team import Team


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
