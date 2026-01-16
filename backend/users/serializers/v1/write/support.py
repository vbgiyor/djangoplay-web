from users.serializers.base import BaseSupportSerializer


class SupportWriteSerializerV1(BaseSupportSerializer):
    class Meta(BaseSupportSerializer.Meta):
        fields = (
            "subject",
            "full_name",
            "email",
            "message",
            "severity",
            "is_bug_report",
            "client_ip",
            "is_active",
        )
