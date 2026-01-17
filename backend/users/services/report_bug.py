import logging
from dataclasses import dataclass
from typing import Optional

from audit.contracts.actor import AuditActor
from audit.contracts.target import AuditTarget
from audit.services import AuditRecorder
from django.db.models import Q
from django.utils import timezone
from mailer.throttling.flow_throttle import allow_flow

from users.models.file_upload import FileUpload
from users.models.support import SupportTicket

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Result object returned to views
# ---------------------------------------------------------------------
@dataclass(frozen=True)
class BugReportResult:

    """
    Result returned to the caller (view / adapter).

    status:
      - "success"
      - "limit"
      - "error"
    """

    status: str
    ticket: Optional[SupportTicket] = None
    error: Optional[str] = None


class BugService:

    """
    Canonical service for bug reports.

    Responsibilities:
      - Create bug report SupportTicket
      - Apply unified allow_flow() throttling
      - Queue email notifications (best effort)

    Does NOT:
      - Perform form validation
      - Touch Django messages
      - Perform redirects
    """

    # ---------------------------------------------------------
    # Optional analytics (not used for enforcement)
    # ---------------------------------------------------------
    @staticmethod
    def count_tickets_today(email=None, employee=None, client_ip=None):
        today = timezone.now().date()
        return (
            SupportTicket.objects.filter(
                is_bug_report=True,
                created_at__date=today
            )
            .filter(Q(email=email) | Q(employee=employee) | Q(client_ip=client_ip))
            .count()
        )

    # ---------------------------------------------------------
    # Main entry point
    # ---------------------------------------------------------
    @staticmethod
    def submit_bug_report(
        *,
        request,
        form,
    ) -> BugReportResult:
        """
        Create a bug report and apply throttling.

        Returns:
            BugReportResult

        """
        employee = request.user if request.user.is_authenticated else None
        email = form.cleaned_data["email"].strip().lower()

        # Canonical request context (middleware-provided)
        client_ip = getattr(request, "client_ip", None)
        request_id = getattr(request, "request_id", None)

        # -----------------------------------------------------
        # 1) Create SupportTicket (always created first)
        # -----------------------------------------------------
        try:
            ticket = SupportTicket(
                is_bug_report=True,
                subject=form.cleaned_data.get("subject") or "Bug Report",
                full_name=email.split("@")[0],
                email=email,
                message=form.cleaned_data.get("message"),
                github_issue=form.cleaned_data.get("github_issue"),
                employee=employee,
                client_ip=client_ip,
            )
            ticket.save(user=employee if employee else None)

            AuditRecorder.record(
                action="bug_report.created",
                actor=AuditActor(
                    id=employee.pk if employee else None,
                    type="user" if employee else "anonymous",
                    label=email,
                ),
                target=AuditTarget(
                    type="support_ticket",
                    id=ticket.id,
                    label=ticket.ticket_number,
                ),
                metadata={
                    "is_bug_report": True,
                    "has_attachments": bool(request.FILES),
                },
            )
            for f in request.FILES.getlist("files"):
                FileUpload.objects.create(
                    content_object=ticket,
                    file=f,
                )

            logger.info(
                "BugService: created bug ticket",
                extra={
                    "ticket_number": ticket.ticket_number,
                    "email": email,
                    "request_id": request_id,
                },
            )

        except Exception as exc:
            logger.exception(
                "BugService: failed to create bug ticket",
                extra={"email": email, "request_id": request_id},
            )
            return BugReportResult(status="error", error=str(exc))

        # -----------------------------------------------------
        # 2) Unified throttling (post-create, mirrors SupportService)
        # -----------------------------------------------------
        allowed, reason, dbg = allow_flow(
            flow="bug_report",
            user_id=employee.pk if employee else None,
            email=email,
            client_ip=client_ip,
            prefer_user_identity=True,
        )

        if not allowed:
            logger.info(
                "BugService: throttled bug report",
                extra={
                    "ticket_number": ticket.ticket_number,
                    "email": email,
                    "user_id": employee.pk if employee else None,
                    "client_ip": client_ip,
                    "reason": reason,
                    "debug": dbg,
                    "request_id": request_id,
                },
            )
            AuditRecorder.record(
                action="bug_report.throttled",
                actor=AuditActor(
                    id=employee.pk if employee else None,
                    type="user" if employee else "anonymous",
                    label=email,
                ),
                target=AuditTarget(
                    type="support_ticket",
                    id=ticket.id,
                    label=ticket.ticket_number,
                ),
                metadata={
                    "reason": reason,
                    "debug": dbg,
                },
            )
            return BugReportResult(status="limit", ticket=ticket)

        # -----------------------------------------------------
        # 3) Queue email notification (best effort)
        # -----------------------------------------------------
        from mailer.flows.member.support import send_support_or_bug_email_task
        try:
            send_support_or_bug_email_task.delay(ticket.id)
            AuditRecorder.record(
                action="bug_report.email_queued",
                actor=AuditActor(
                    id=employee.pk if employee else None,
                    type="user" if employee else "anonymous",
                    label=email,
                ),
                target=AuditTarget(
                    type="support_ticket",
                    id=ticket.id,
                    label=ticket.ticket_number,
                ),
                metadata={
                    "task": "send_support_or_bug_email_task",
                },
                is_system_event=True,
            )
            logger.info(
                "BugService: queued email task",
                extra={
                    "ticket_number": ticket.ticket_number,
                    "request_id": request_id,
                },
            )
            return BugReportResult(status="success", ticket=ticket)

        except Exception as exc:
            logger.exception(
                "BugService: failed to queue email task",
                extra={
                    "ticket_number": ticket.ticket_number,
                    "request_id": request_id,
                },
            )
            AuditRecorder.record(
                action="bug_report.email_failed",
                actor=AuditActor(
                    id=employee.pk if employee else None,
                    type="user" if employee else "anonymous",
                    label=email,
                ),
                target=AuditTarget(
                    type="support_ticket",
                    id=ticket.id,
                    label=ticket.ticket_number,
                ),
                metadata={
                    "error": str(exc),
                },
                is_system_event=True,
            )
            return BugReportResult(status="error", ticket=ticket, error=str(exc))
