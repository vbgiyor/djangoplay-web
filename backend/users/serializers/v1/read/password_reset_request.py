from users.serializers.base import BasePasswordResetRequestSerializer


class PasswordResetRequestReadSerializerV1(BasePasswordResetRequestSerializer):
    class Meta(BasePasswordResetRequestSerializer.Meta):
        fields = BasePasswordResetRequestSerializer.Meta.fields + (
            "created_at",
            "updated_at",
        )
