# paystream/apps.py
from django.apps import AppConfig


class PaystreamConfig(AppConfig):
    name = "paystream"

    def ready(self):
        # Import services
        from paystream.services.runtime_site import ensure_runtime_site
        from paystream.services.socialapps import ensure_google_socialapp

        # Execute auto-setup
        ensure_runtime_site()
        ensure_google_socialapp()
