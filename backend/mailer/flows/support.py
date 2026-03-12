import logging
from typing import Any

from celery import shared_task
from django.conf import settings
from helpdesk.models import SupportTicket
from utilities.admin.url_utils import get_admin_url
from utilities.constants.template_registry import TemplateRegistry as T

from mailer.engine.base import send_email_via_adapter

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_support_ticket_email_task(self: Any, ticket_id: int) -> None:
    try:
        ticket = (
            SupportTicket.objects
            .select_related("user")
            .prefetch_related("attachments")
            .get(pk=ticket_id)
        )
    except SupportTicket.DoesNotExist:
        logger.warning("Support ticket %s not found", ticket_id)
        return

    # --------------------------------------------------
    # Idempotency guard (FIRST)
    # --------------------------------------------------
    if ticket.emails_sent:
        logger.info(
            "Support ticket %s email already sent — skipping",
            ticket.ticket_number,
        )
        return

    file_names = [
        f.file.name.split("/")[-1]
        for f in ticket.attachments.all()
        if f.file
    ]

    context = {
        "ticket": ticket,
        "ticket_kind": "support",
        "admin_url": get_admin_url(ticket),
        "file_names": file_names,
        "has_attachments": bool(file_names),
        "site_name": getattr(settings, "SITE_NAME", "DjangoPlay"),
    }


    # --------------------------------------------------
    # Send emails (best effort, but all-or-nothing)
    # --------------------------------------------------
    try:
        send_email_via_adapter(
            template_prefix=T.REQUEST_TO_SUPPORT_EMAIL,
            to_email=settings.SUPPORT_EMAIL,
            context=context,
        )

        send_email_via_adapter(
            template_prefix=T.CONFIRMATION_TO_USER_EMAIL,
            to_email=ticket.email,
            context=context,
            user=ticket.user,
        )

    except Exception as exc:
        logger.exception(
            "Support ticket %s email send failed — will retry",
            ticket.ticket_number,
        )
        raise self.retry(exc=exc)

    # --------------------------------------------------
    # Mark as sent ONLY after success
    # --------------------------------------------------
    updated = (
        SupportTicket.objects
        .filter(pk=ticket.id, emails_sent=False)
        .update(emails_sent=True)
    )

    if not updated:
        logger.info(
            "Support ticket %s email already marked as sent by another worker",
            ticket.ticket_number,
        )

    logger.info(
        "Support ticket %s email marked as sent",
        ticket.ticket_number,
    )
