from rest_framework import serializers

from users.models.leave_balance import LeaveBalance


class BaseLeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = (
            "id",
            "employee",
            "leave_type",
            "year",
            "balance",
            "used",
            "reset_date",
            "is_active",
        )
        read_only_fields = ("id", "used")
