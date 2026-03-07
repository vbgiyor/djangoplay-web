import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from core.middleware import thread_local
from mailer.flows.support import (
    send_support_ticket_email_task,
)
from mailer.throttling.flow_throttle import allow_flow
from paystream.integrations.issuetracker.ui.services.issue_mutation_service import IssueMutationService
from users.services.identity_query_service import IdentityQueryService

from helpdesk.adapters.issue_adapter import IssueAdapter
from helpdesk.models import FileUpload, SupportStatus, SupportTicket

logger = logging.getLogger(__name__)


@dataclass
class SupportRequestResult:

    """
    Result object returned to the view for support ticket submissions.
    """

    status: str  # "success", "limit", "not_registered", "error"
    ticket: SupportTicket | None = None
    error: str | None = None


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
    # @staticmethod
    # def _is_registered_email(email_lc: str) -> bool:
    #     return (
    #         Employee.objects.filter(email__iexact=email_lc, deleted_at__isnull=True).exists()
    #         or MemberProfile.objects.filter(email__iexact=email_lc, deleted_at__isnull=True).exists()
    #     )

    @staticmethod
    def _is_registered_email(email_lc: str) -> bool:
        return bool(IdentityQueryService.get_by_email(email_lc))


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
                ticket.user = employee

            ticket.save()

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
        # Sync Support Ticket → IssueTracker
        # -----------------------------------------------------
        try:
            SupportService.sync_ticket_to_issue(ticket, request)
        except Exception:
            logger.exception(
                "SupportService: Ticket sync failed",
                extra={"ticket_number": ticket.ticket_number},
            )

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
            send_support_ticket_email_task.delay(ticket.id)
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


    @staticmethod
    def sync_ticket_to_issue(ticket, request):
        """
        This sync allows to show corresponding SupportTicket on issues subdomain.
        But currently with v1.1.0, not included in UI changes.
        Will be integrated at the time when support tickets will be publicly displayed.      
        """
        if getattr(ticket, "migrated_issue_id", None):
            return None

        reporter_user_id = None

        if request.user.is_authenticated:
            reporter_user_id = request.user.id

        payload = IssueAdapter.build_support_issue_payload(
            ticket,
            reporter_user_id=reporter_user_id,
        )

        issue = IssueMutationService.create_issue(
            user=request.user,
            **payload,
        )

        ticket.migrated_issue_id = issue.id
        ticket.save(update_fields=["migrated_issue_id"])

        return issue
