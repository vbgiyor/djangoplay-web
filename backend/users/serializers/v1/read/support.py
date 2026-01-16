from users.serializers.base import BaseSupportSerializer


class SupportReadSerializerV1(BaseSupportSerializer):
    class Meta(BaseSupportSerializer.Meta):
        fields = BaseSupportSerializer.Meta.fields + (
            "created_at",
            "updated_at",
        )
