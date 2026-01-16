from users.serializers.base import BaseSignUpRequestSerializer


class SignUpRequestReadSerializerV1(BaseSignUpRequestSerializer):
    class Meta(BaseSignUpRequestSerializer.Meta):
        fields = BaseSignUpRequestSerializer.Meta.fields + (
            "created_at",
            "updated_at",
        )
