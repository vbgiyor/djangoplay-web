from rest_framework import serializers

from teamcentral.models import LeaveType


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
