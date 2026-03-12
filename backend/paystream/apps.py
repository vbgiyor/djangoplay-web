from django.apps import AppConfig


class PaystreamConfig(AppConfig):
    name = "paystream"

    def ready(self):
        from django.db import connection
        from django.db.utils import OperationalError, ProgrammingError

        try:
            # Check if tables exist before running DB-dependent setup
            table_names = connection.introspection.table_names()
            if "django_site" not in table_names:
                return
        except (OperationalError, ProgrammingError):
            return

        from paystream.services.runtime_site import ensure_runtime_site
        from paystream.services.socialapps import ensure_google_socialapp

        ensure_runtime_site()
        ensure_google_socialapp()