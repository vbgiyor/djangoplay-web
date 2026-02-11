from teamcentral.serializers.base import BaseTeamSerializer


class TeamWriteSerializerV1(BaseTeamSerializer):
    class Meta(BaseTeamSerializer.Meta):
        fields = (
            "name",
            "department",
            "leader",
            "description",
            "is_active",
        )
