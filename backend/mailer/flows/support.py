import logging
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from core.middleware import thread_local
from users.models import (
    Employee,
    FileUpload,
    Member,
    SupportStatus,
    SupportTicket,
)

from mailer.flows.member.support import (
    send_support_or_bug_email_task,
)
from mailer.throttling.flow_throttle import allow_flow

logger = logging.getLogger(__name__)


@dataclass
class SupportRequestResult:

    """
    Result object returned to the view for support ticket submissions.
    """

    status: str  # "success", "limit", "not_registered", "error"
    ticket: Optional[SupportTicket] = None
    error: Optional[str] = None


class SupportService:

    """
    Service to handle Support Ticket creation + unified throttling + email.

    View responsibilities:
      - validate form
      - messages + redirect

    Service responsibilities:
      - validate email ownership
      - create SupportTicket + FileUploads
      - queue Celery task best-effort
    """

    # --------------------------------------------------------- #
    # Registered email check
    # --------------------------------------------------------- #
    @staticmethod
    def _is_registered_email(email_lc: str) -> bool:
        return (
            Employee.objects.filter(email__iexact=email_lc, deleted_at__isnull=True).exists()
            or Member.objects.filter(email__iexact=email_lc, deleted_at__isnull=True).exists()
        )

    # --------------------------------------------------------- #
    # Main entrypoint
    # --------------------------------------------------------- #
    @staticmethod
    def submit_support_request(
        *,
        request,
        subject: str,
        full_name: str,
        email: str,
        message: str,
        files: Iterable[Any],
    ) -> SupportRequestResult:

        email_lc = (email or "").strip().lower()

        # -----------------------------------------------------
        # 1) Email must belong to an Employee or Member
        # -----------------------------------------------------
        # Allow unregistered users — treat as new visitors.
        is_registered = SupportService._is_registered_email(email_lc)
        if not is_registered:
            logger.info("SupportService: %s is NOT registered — proceeding as guest user", email_lc)

        employee = request.user if request.user.is_authenticated else None

        # -----------------------------------------------------
        # 2) Create ticket + file uploads
        # -----------------------------------------------------
        try:
            ticket = SupportTicket(
                subject=subject,
                full_name=full_name,
                email=email_lc,
                message=message,
                status=SupportStatus.OPEN,
            )

            if employee:
                ticket.employee = employee

            ticket.save(user=employee if employee else None)

            for f in files:
                FileUpload.objects.create(
                    content_object=ticket,
                    file=f,
                )

            logger.info(
                "SupportService: created support ticket #%s for %s",
                ticket.ticket_number,
                email_lc,
            )

        except Exception as e:
            logger.exception("SupportService: failed to create support ticket: %s", e)
            return SupportRequestResult(status="error", ticket=None, error=str(e))

        # -----------------------------------------------------
        # 3) Unified throttle check — applies to all users
        # Unregistered users will throttle via per_email & per_ip
        # -----------------------------------------------------
        ip_value = getattr(thread_local, "client_ip", request.META.get("REMOTE_ADDR"))

        allowed, reason, dbg = allow_flow(
            flow="support_request",
            user_id=employee.pk if employee else None,
            email=email_lc,
            client_ip=ip_value,
            prefer_user_identity=False,   # (email → ip)
        )

        if not allowed:
            logger.info(
                "SupportService: throttled support_request email=%s user_id=%s ip=%s reason=%s dbg=%s",
                email_lc,
                employee.pk if employee else None,
                ip_value,
                reason,
                dbg,
            )
            return SupportRequestResult(status="limit", ticket=ticket)

        # -----------------------------------------------------
        # 4) Queue Celery email
        # -----------------------------------------------------
        try:
            send_support_or_bug_email_task.delay(ticket.id)
            logger.info(
                "SupportService: queued email task for support ticket #%s",
                ticket.ticket_number,
            )
            return SupportRequestResult(status="success", ticket=ticket)

        except Exception as e:
            logger.exception(
                "SupportService: failed to queue support ticket email for #%s: %s",
                ticket.ticket_number,
                e,
            )
            return SupportRequestResult(status="error", ticket=ticket, error=str(e))
