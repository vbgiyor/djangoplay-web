from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "audit"

    def ready(self):
        """
        Register audit lifecycle signal handlers.

        Important:
        - Import happens here to avoid early model loading
        - Signals are observational only
        - No domain logic is executed at import time

        """
        from audit.signals import lifecycle  # noqa: F401
