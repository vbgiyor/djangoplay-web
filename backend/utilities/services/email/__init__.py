# import logging

# from celery import current_app as celery_app

# logger = logging.getLogger(__name__)


# def register_email_tasks(sender=None, **kwargs):
#     """
#     Import all modules that define email-related Celery tasks.
#     """
#     logger.info("Registering email Celery tasks for utilities.services.email")

#     # Import the modules that contain @shared_task definitions.
#     # import utilities.services.email.password_reset  # noqa: F401
#     import utilities.services.email.member_notifications  # noqa: F401

# # Hook into Celery after configuration.
# celery_app.on_after_configure.connect(register_email_tasks)
