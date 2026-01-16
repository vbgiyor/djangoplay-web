from users.serializers.base import BasePasswordResetRequestSerializer


class PasswordResetRequestWriteSerializerV1(BasePasswordResetRequestSerializer):
    class Meta(BasePasswordResetRequestSerializer.Meta):
        fields = (
            "user",
            "expires_at",
        )
