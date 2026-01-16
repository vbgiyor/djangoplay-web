from users.serializers.base import BaseEmployeeSerializer


class EmployeeReadSerializerV1(BaseEmployeeSerializer):
    class Meta(BaseEmployeeSerializer.Meta):
        fields = BaseEmployeeSerializer.Meta.fields + (
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )
