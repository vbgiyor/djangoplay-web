from rest_framework import serializers

from users.models.employee_type import EmployeeType


class BaseEmployeeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeType
        fields = (
            "id",
            "code",
            "name",
            "is_active",
        )
        read_only_fields = ("id",)
