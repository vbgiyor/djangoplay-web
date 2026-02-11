from rest_framework import serializers

from teamcentral.models import MemberProfile


class BaseMemberProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberProfile
        fields = (
            "id",
            "member_code",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "address",
            "status",
            "employee",
            "is_active",
        )
        read_only_fields = ("id", "member_code")
