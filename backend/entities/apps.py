from django.apps import AppConfig


class EntitiesConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'entities'
    # name = 'businesses'

    def ready(self):
        # import entities.signals  # Connect signals
        pass
