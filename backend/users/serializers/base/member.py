from rest_framework import serializers

from users.models.member import Member


class BaseMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
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
