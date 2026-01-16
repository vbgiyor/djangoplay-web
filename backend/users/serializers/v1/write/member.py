from users.serializers.base import BaseMemberSerializer


class MemberWriteSerializerV1(BaseMemberSerializer):
    class Meta(BaseMemberSerializer.Meta):
        fields = (
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "address",
            "status",
            "is_active",
        )
