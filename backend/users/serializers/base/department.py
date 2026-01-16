from rest_framework import serializers

from users.models.department import Department


class BaseDepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = (
            "id",
            "name",
            "code",
            "is_active",
        )
        read_only_fields = ("id",)
