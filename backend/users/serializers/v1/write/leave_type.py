from users.serializers.base import BaseLeaveTypeSerializer


class LeaveTypeWriteSerializerV1(BaseLeaveTypeSerializer):
    class Meta(BaseLeaveTypeSerializer.Meta):
        fields = (
            "code",
            "name",
            "default_balance",
            "is_active",
        )
