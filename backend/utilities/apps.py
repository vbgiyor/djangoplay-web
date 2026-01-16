import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class UtilitiesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "utilities"

    def ready(self):
        """
        Called by Django when the 'utilities' app is fully loaded.

        We import utilities.services.email here so that its module-level
        Celery hooks (on_after_configure.connect) are registered.

        Any detailed logging about task registration is handled inside
        utilities.services.email itself (e.g. register_email_tasks),
        to avoid coupling this app config to management commands or
        Django's process startup semantics.
        """
        try:
            import utilities.services.email  # noqa: F401
        except Exception as e:
            logger.exception(
                "UtilitiesConfig.ready: failed to import utilities.services.email: %s",
                e,
            )
