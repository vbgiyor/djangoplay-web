from users.serializers.base import BaseMemberStatusSerializer


class MemberStatusReadSerializerV1(BaseMemberStatusSerializer):
    class Meta(BaseMemberStatusSerializer.Meta):
        fields = BaseMemberStatusSerializer.Meta.fields + (
            "created_at",
            "updated_at",
        )
