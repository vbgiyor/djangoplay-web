from rest_framework import serializers

from users.models.password_reset_request import PasswordResetRequest


class BasePasswordResetRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PasswordResetRequest
        fields = (
            "id",
            "user",
            "token",
            "expires_at",
            "used",
        )
        read_only_fields = ("id", "token", "used")
