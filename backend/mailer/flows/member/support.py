import logging
from typing import Any

from celery import shared_task
from django.conf import settings

from users.models import SupportTicket
from utilities.admin.url_utils import get_site_base_url, get_admin_url
from utilities.constants.template_registry import TemplateRegistry as T

from mailer.engine.base import send_email_via_adapter

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_support_or_bug_email_task(self: Any, ticket_id: int) -> None:
    try:
        ticket = (
            SupportTicket.objects
            .select_related("employee")
            .prefetch_related("file_uploads")
            .get(pk=ticket_id)
        )
    except SupportTicket.DoesNotExist:
        logger.warning(
            "send_support_or_bug_email_task: ticket_id=%s not found",
            ticket_id,
        )
        return

    if ticket.email and ticket.email.lower().strip() == "redstar@djangoplay.com":
        logger.info("Skipping email for redstar")
        ticket.emails_sent = True
        ticket.save(update_fields=["emails_sent"])
        return

    if getattr(ticket, "emails_sent", False):
        logger.info("Emails already sent for ticket %s", ticket_id)
        return

    file_uploads = ticket.file_uploads.all()
    file_names = [
        f.file.name.split("/")[-1]
        for f in file_uploads
        if f.file
    ]

    context = {
        "ticket": ticket,
        "site_name": getattr(settings, "SITE_NAME", "DjangoPlay"),
        "admin_url": get_admin_url(ticket),
        "file_names": file_names,
        "file_count": len(file_uploads),
        "has_attachments": bool(file_uploads),
        "user": ticket.employee,
        "employee_id": ticket.employee.id if ticket.employee else None,
    }

    # Admin notification
    send_email_via_adapter(
        template_prefix=T.REQUEST_TO_SUPPORT_EMAIL,
        to_email=settings.DEFAULT_FROM_EMAIL,
        context=context,
    )

    # User confirmation
    send_email_via_adapter(
        template_prefix=T.CONFIRMATION_TO_USER_EMAIL,
        to_email=ticket.email,
        context=context,
        user=ticket.employee,
    )

    ticket.emails_sent = True
    ticket.save(update_fields=["emails_sent"])

    logger.info(
        "Emails sent for ticket %s (bug=%s)",
        ticket_id,
        ticket.is_bug_report,
    )
