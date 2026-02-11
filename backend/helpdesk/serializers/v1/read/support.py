from helpdesk.serializers.base.support import BaseSupportSerializer


class SupportReadSerializerV1(BaseSupportSerializer):

    """
    Read-only serializer for support tickets (V1).
    """

    class Meta(BaseSupportSerializer.Meta):
        fields = BaseSupportSerializer.Meta.fields + (
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )
