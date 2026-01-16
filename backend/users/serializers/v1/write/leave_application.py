from users.serializers.base import BaseLeaveApplicationSerializer


class LeaveApplicationWriteSerializerV1(BaseLeaveApplicationSerializer):
    class Meta(BaseLeaveApplicationSerializer.Meta):
        fields = (
            "employee",
            "leave_type",
            "start_date",
            "end_date",
            "hours",
            "reason",
        )
