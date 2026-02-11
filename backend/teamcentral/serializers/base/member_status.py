from rest_framework import serializers

from teamcentral.models import MemberStatus


class BaseMemberStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberStatus
        fields = (
            "id",
            "code",
            "name",
            "is_active",
        )
        read_only_fields = ("id",)
