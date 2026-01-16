from users.serializers.base import BaseUserActivityLogSerializer


class UserActivityLogWriteSerializerV1(BaseUserActivityLogSerializer):

    """
    Write serializer exists ONLY for internal/system usage.
    Public APIs must never expose write access.
    """

    class Meta(BaseUserActivityLogSerializer.Meta):
        fields = (
            "user",
            "action",
            "client_ip",
        )
