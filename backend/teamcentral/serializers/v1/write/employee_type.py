from teamcentral.serializers.base import BaseEmployeeTypeSerializer


class EmployeeTypeWriteSerializerV1(BaseEmployeeTypeSerializer):
    class Meta(BaseEmployeeTypeSerializer.Meta):
        fields = (
            "code",
            "name",
            "is_active",
        )
