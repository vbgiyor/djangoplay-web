from teamcentral.serializers.base import BaseMemberProfileSerializer


class MemberProfileWriteSerializerV1(BaseMemberProfileSerializer):
    class Meta(BaseMemberProfileSerializer.Meta):
        fields = (
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "address",
            "status",
            "is_active",
        )
