"""
Celery task registry for the mailer app.

This module exists ONLY to expose mailer-owned tasks
to Celery autodiscovery.

No logic should live here.
"""

# Email flows
from mailer.flows.password_reset import send_password_reset_email_task  # noqa
from mailer.flows.resend_verification import resend_verification_for_email_task  # noqa
from mailer.flows.support import send_support_ticket_email_task  # noqa
from mailer.flows.bug import send_bug_report_email_task  # noqa
