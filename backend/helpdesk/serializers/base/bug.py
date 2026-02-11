from rest_framework import serializers

from helpdesk.models import BugReport


class BaseBugReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = BugReport
        fields = (
            "id",
            "bug_number",
            "summary",
            "steps_to_reproduce",
            "expected_result",
            "actual_result",
            "status",
            "severity",
            "external_issue_url",
            "emails_sent",
            "reporter",
        )
        read_only_fields = (
            "id",
            "bug_number",
        )
