from teamcentral.serializers.base import BaseDepartmentSerializer


class DepartmentReadSerializerV1(BaseDepartmentSerializer):
    class Meta(BaseDepartmentSerializer.Meta):
        fields = BaseDepartmentSerializer.Meta.fields + (
            "created_at",
            "updated_at",
        )
