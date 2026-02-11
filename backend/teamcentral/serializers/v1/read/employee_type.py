from teamcentral.serializers.base import BaseEmployeeTypeSerializer


class EmployeeTypeReadSerializerV1(BaseEmployeeTypeSerializer):
    class Meta(BaseEmployeeTypeSerializer.Meta):
        fields = BaseEmployeeTypeSerializer.Meta.fields + (
            "created_at",
            "updated_at",
        )
