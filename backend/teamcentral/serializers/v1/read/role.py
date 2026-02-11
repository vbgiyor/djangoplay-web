from teamcentral.serializers.base import BaseRoleSerializer


class RoleReadSerializerV1(BaseRoleSerializer):
    class Meta(BaseRoleSerializer.Meta):
        fields = BaseRoleSerializer.Meta.fields + (
            "created_at",
            "updated_at",
        )
