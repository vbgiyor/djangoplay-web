from users.serializers.base import BaseSignUpRequestSerializer


class SignUpRequestWriteSerializerV1(BaseSignUpRequestSerializer):
    class Meta(BaseSignUpRequestSerializer.Meta):
        fields = (
            "user",
            "sso_provider",
            "sso_id",
            "expires_at",
        )
