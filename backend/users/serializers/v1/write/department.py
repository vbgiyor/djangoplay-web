from users.serializers.base import BaseDepartmentSerializer


class DepartmentWriteSerializerV1(BaseDepartmentSerializer):
    class Meta(BaseDepartmentSerializer.Meta):
        fields = (
            "name",
            "code",
            "is_active",
        )
