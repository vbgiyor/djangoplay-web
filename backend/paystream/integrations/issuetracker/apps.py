from django.apps import AppConfig


class IssueTrackerIntegrationConfig(AppConfig):

    """
    Integration adapter between DjangoPlay and GenericIssueTracker.
    """

    name = "paystream.integrations.issuetracker"
    verbose_name = "Issue Tracker Integration"

    def ready(self):

        from . import signals  # noqa

        # Bootstrap labels once at startup
        try:
            from paystream.integrations.issuetracker.services.label_bootstrap import (
                IssueLabelBootstrapService,
            )

            IssueLabelBootstrapService.ensure_labels_exist()

        except Exception:
            # Avoid breaking app startup if DB isn't ready
            pass
