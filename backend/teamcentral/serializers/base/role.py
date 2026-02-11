from rest_framework import serializers

from teamcentral.models import Role


class BaseRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = (
            "id",
            "code",
            "title",
            "is_active",
        )
        read_only_fields = ("id",)
