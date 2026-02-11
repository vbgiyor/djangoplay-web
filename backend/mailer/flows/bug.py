import logging
from typing import Any

from celery import shared_task
from django.conf import settings
from helpdesk.models import BugReport
from utilities.admin.url_utils import get_admin_url
from utilities.constants.template_registry import TemplateRegistry as T

from mailer.engine.base import send_email_via_adapter

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_bug_report_email_task(self: Any, bug_id: int) -> None:
    try:
        bug = (
            BugReport.objects
            .select_related("reporter")
            .prefetch_related("attachments")
            .get(pk=bug_id)
        )
    except BugReport.DoesNotExist:
        logger.warning("Bug report %s not found", bug_id)
        return

    # --------------------------------------------------
    # Idempotency guard (FIRST)
    # --------------------------------------------------
    if bug.emails_sent:
        logger.info("Bug report %s email already sent — skipping", bug.bug_number)
        return

    file_names = [
        f.file.name.split("/")[-1]
        for f in bug.attachments.all()
        if f.file
    ]

    context = {
        "bug": bug,
        "ticket_kind": "bug",
        "admin_url": get_admin_url(bug),
        "file_names": file_names,
        "has_attachments": bool(file_names),
        "site_name": getattr(settings, "SITE_NAME", "DjangoPlay"),
    }

    # --------------------------------------------------
    # Send emails (best effort, but all-or-nothing)
    # --------------------------------------------------
    try:
        # Admin notification
        send_email_via_adapter(
            template_prefix=T.REQUEST_TO_SUPPORT_EMAIL,
            to_email=settings.DEFAULT_FROM_EMAIL,
            context=context,
        )

        # Reporter confirmation
        send_email_via_adapter(
            template_prefix=T.CONFIRMATION_TO_USER_EMAIL,
            to_email=bug.reporter.email,
            context=context,
            user=bug.reporter,
        )

    except Exception as exc:
        logger.exception(
            "Bug report %s email send failed — will retry",
            bug.bug_number,
        )
        raise self.retry(exc=exc)

    # --------------------------------------------------
    # Mark as sent ONLY after success
    # --------------------------------------------------
    updated = (
        BugReport.objects
        .filter(pk=bug.id, emails_sent=False)
        .update(emails_sent=True)
    )

    if not updated:
        logger.info(
            "Bug report %s email already marked as sent",
            bug.bug_number,
        )

    logger.info("Bug report %s email marked as sent", bug.bug_number)
