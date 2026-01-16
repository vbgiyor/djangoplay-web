from rest_framework import serializers

from users.models.member_status import MemberStatus


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
