from django.apps import AppConfig


class FincoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fincore'

    def ready(self):
        """Connect signals for the fincore app."""
        # import fincore.signals  # Ensure signals are connected
        pass
