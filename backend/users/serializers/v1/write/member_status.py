from users.serializers.base import BaseMemberStatusSerializer


class MemberStatusWriteSerializerV1(BaseMemberStatusSerializer):
    class Meta(BaseMemberStatusSerializer.Meta):
        fields = (
            "code",
            "name",
            "is_active",
        )
