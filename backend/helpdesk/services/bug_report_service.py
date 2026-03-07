import logging
from dataclasses import dataclass

from audit.contracts.actor import AuditActor
from audit.contracts.target import AuditTarget
from audit.services import AuditRecorder
from django.db.models import Q
from django.utils import timezone
from mailer.flows.bug import send_bug_report_email_task
from mailer.throttling.flow_throttle import allow_flow
from paystream.integrations.issuetracker.ui.services.issue_mutation_service import IssueMutationService

from helpdesk.adapters.issue_adapter import IssueAdapter
from helpdesk.models import BugReport, FileUpload

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
    bug: BugReport | None = None
    error: str | None = None


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
            BugReport.objects.filter(
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
        # 1) Create Bug
        # -----------------------------------------------------
        try:
            bug = BugReport(
                reporter=employee,
                summary=form.cleaned_data.get("subject") or "Bug Report",
                steps_to_reproduce=form.cleaned_data["message"],
                external_issue_url=form.cleaned_data.get("github_issue", ""),
            )
            bug.save()

            AuditRecorder.record(
                action="bug_report.created",
                actor=AuditActor(
                    id=employee.pk if employee else None,
                    type="user" if employee else "anonymous",
                    label=email,
                ),
                target=AuditTarget(
                    type="bug_report",
                    id=bug.id,
                    label=bug.bug_number,
                ),

            )

            for f in request.FILES.getlist("files"):
                FileUpload.objects.create(
                    content_object=bug,
                    file=f,
                )

            logger.info(
                "BugService: created bug ticket",
                extra={
                    "bug_number": bug.bug_number,
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
        # Sync Bug → IssueTracker
        # -----------------------------------------------------
        try:
            BugService.sync_bug_to_issue(bug, request)
        except Exception:
            logger.exception(
                "BugService: Issue sync failed",
                extra={"bug_number": bug.bug_number},
            )

        # -----------------------------------------------------
        # 2) Unified throttling
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
                    "bug_number": bug.bug_number,
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
                    type="bug_report",
                    id=bug.id,
                    label=bug.bug_number,
                ),
                metadata={
                    "reason": reason,
                    "debug": dbg,
                },
            )
            return BugReportResult(status="limit", bug=bug)

        # -----------------------------------------------------
        # 3) Queue email notification (best effort)
        # -----------------------------------------------------
        try:
            send_bug_report_email_task.delay(bug.id)
            AuditRecorder.record(
                action="bug_report.email_queued",
                actor=AuditActor(
                    id=employee.pk if employee else None,
                    type="user" if employee else "anonymous",
                    label=email,
                ),
                target=AuditTarget(
                    type="bug_report",
                    id=bug.id,
                    label=bug.bug_number,
                ),
                metadata={
                    "task": "send_support_or_bug_email_task",
                },
                is_system_event=True,
            )
            logger.info(
                "BugService: queued email task",
                extra={
                    "bug_number": bug.bug_number,
                    "request_id": request_id,
                },
            )
            return BugReportResult(status="success", bug=bug)

        except Exception as exc:
            logger.exception(
                "BugService: failed to queue email task",
                extra={
                    "bug_number": bug.bug_number,
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
                    type="bug_report",
                    id=bug.id,
                    label=bug.bug_number,
                ),
                metadata={
                    "error": str(exc),
                },
                is_system_event=True,
            )
            return BugReportResult(status="error", bug=bug, error=str(exc))


    @staticmethod
    def sync_bug_to_issue(bug, request):
        """
        Creates Issue corresponding to BugReport.
        """
        if getattr(bug, "migrated_issue_id", None):
            return None

        reporter_user_id = None

        if request.user.is_authenticated:
            reporter_user_id = request.user.id

        payload = IssueAdapter.build_bug_issue_payload(
            bug,
            reporter_user_id=reporter_user_id,
        )

        # enforce as internal issue created from host app
        payload["is_public"] = False

        result = IssueMutationService.create_issue(
            request=request,
            data=payload,
        )

        if not result.success:
            raise Exception(result.error)

        issue = result.issue

        bug.migrated_issue_id = issue.id
        bug.save(update_fields=["migrated_issue_id"])

        return issue
