from rest_framework import serializers

from users.models.leave_application import LeaveApplication


class BaseLeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = (
            "id",
            "employee",
            "leave_type",
            "start_date",
            "end_date",
            "hours",
            "status",
            "approver",
            "reason",
            "is_active",
        )
        read_only_fields = ("id", "status", "approver")
