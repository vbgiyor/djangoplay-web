from users.serializers.base import BaseRoleSerializer


class RoleWriteSerializerV1(BaseRoleSerializer):
    class Meta(BaseRoleSerializer.Meta):
        fields = (
            "code",
            "title",
            "rank",
            "is_active",
        )
