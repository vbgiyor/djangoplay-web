import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)

class UsersConfig(AppConfig):
    name = 'users'
    verbose_name = 'Users'

    def ready(self):
        pass
