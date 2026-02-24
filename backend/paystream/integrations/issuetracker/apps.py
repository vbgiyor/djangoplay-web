from django.apps import AppConfig


class IssueTrackerIntegrationConfig(AppConfig):

    """
    Integration adapter between DjangoPlay and GenericIssueTracker.
    """

    name = "paystream.integrations.issuetracker"
    verbose_name = "Issue Tracker Integration"

    def ready(self):
        from . import signals  # noqa
