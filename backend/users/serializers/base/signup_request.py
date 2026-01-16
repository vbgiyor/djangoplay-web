from rest_framework import serializers

from users.models.signup_request import SignUpRequest


class BaseSignUpRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignUpRequest
        fields = (
            "id",
            "user",
            "sso_provider",
            "sso_id",
            "expires_at",
        )
        read_only_fields = ("id",)
