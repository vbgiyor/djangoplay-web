from helpdesk.serializers.base import BaseBugReportSerializer


class BugReportReadSerializerV1(BaseBugReportSerializer):

    """
    Read-only serializer for bug reports (V1).
    """

    class Meta(BaseBugReportSerializer.Meta):
        fields = BaseBugReportSerializer.Meta.fields + (
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )
