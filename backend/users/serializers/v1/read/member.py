from users.serializers.base import BaseMemberSerializer


class MemberReadSerializerV1(BaseMemberSerializer):
    class Meta(BaseMemberSerializer.Meta):
        fields = BaseMemberSerializer.Meta.fields + (
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )
