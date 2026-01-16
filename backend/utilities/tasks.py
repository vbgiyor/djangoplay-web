# utilities/tasks.py
"""
Celery task registry for the utilities app.

This module exists ONLY to expose service-layer tasks
to Celery autodiscovery.
"""

# Email tasks
import utilities.services.email.password_reset  # noqa
import utilities.services.email.member_notifications  # noqa
