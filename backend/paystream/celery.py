import os
import warnings

from celery import Celery

# ---------------------------------------------------------------------
# Silence "Accessing the database during app initialization is discouraged"
# RuntimeWarning in Celery processes as well.
# ---------------------------------------------------------------------
warnings.filterwarnings(
    "ignore",
    message=r"Accessing the database during app initialization is discouraged.*",
    category=RuntimeWarning,
)

# Set the default Django settings module for the 'celery' program.
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "paystream.settings")

# Create the Celery application instance
app = Celery("paystream")

# Load configuration from Django settings (CELERY_* settings)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover tasks in installed apps
app.autodiscover_tasks()

# Make sure the celery app is available to Django
__all__ = ("app",)
