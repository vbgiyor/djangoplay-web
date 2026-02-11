from rest_framework import serializers

from teamcentral.models import EmploymentStatus


class BaseEmploymentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmploymentStatus
        fields = (
            "id",
            "code",
            "name",
            "is_active",
        )
        read_only_fields = ("id",)
