from helpdesk.serializers.base import BaseBugReportSerializer


class BugReportWriteSerializerV1(BaseBugReportSerializer):

    """
    Write serializer for bug reports.
    """

    class Meta(BaseBugReportSerializer.Meta):
        read_only_fields = BaseBugReportSerializer.Meta.read_only_fields + (
            "emails_sent",
        )
