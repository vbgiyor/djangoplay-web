from teamcentral.serializers.base import BaseTeamSerializer


class TeamReadSerializerV1(BaseTeamSerializer):
    class Meta(BaseTeamSerializer.Meta):
        fields = BaseTeamSerializer.Meta.fields + (
            "created_at",
            "updated_at",
        )
