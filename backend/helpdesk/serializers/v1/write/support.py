from helpdesk.serializers.base.support import BaseSupportSerializer


class SupportWriteSerializerV1(BaseSupportSerializer):

    """
    Write serializer for support tickets (V1).
    """

    class Meta(BaseSupportSerializer.Meta):
        read_only_fields = BaseSupportSerializer.Meta.read_only_fields + (
            "status",
            "resolved_at",
            "emails_sent",
        )
