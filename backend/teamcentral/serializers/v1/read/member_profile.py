from teamcentral.serializers.base import BaseMemberProfileSerializer


class MemberProfileReadSerializerV1(BaseMemberProfileSerializer):
    class Meta(BaseMemberProfileSerializer.Meta):
        fields = BaseMemberProfileSerializer.Meta.fields + (
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )
