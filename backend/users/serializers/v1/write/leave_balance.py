from users.serializers.base import BaseLeaveBalanceSerializer


class LeaveBalanceWriteSerializerV1(BaseLeaveBalanceSerializer):
    class Meta(BaseLeaveBalanceSerializer.Meta):
        fields = (
            "employee",
            "leave_type",
            "year",
            "balance",
            "reset_date",
            "is_active",
        )
