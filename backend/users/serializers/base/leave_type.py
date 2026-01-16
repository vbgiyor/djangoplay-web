from rest_framework import serializers

from users.models.leave_type import LeaveType


class BaseLeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = (
            "id",
            "code",
            "name",
            "default_balance",
            "is_active",
        )
        read_only_fields = ("id",)
