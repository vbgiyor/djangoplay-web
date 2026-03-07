from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from genericissuetracker.serializers.v1.write.issue import (
    IssueCreateSerializer,
)
from helpdesk.adapters.issue_adapter import IssueAdapter
from helpdesk.models import BugReport, SupportTicket
from paystream.integrations.issuetracker.ui.services.issue_mutation_service import (
    IssueMutationService,
)

User = get_user_model()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def build_system_request():
    """
    Build a minimal request-like object required by serializers/services.
    """
    system_user = User.objects.filter(is_superuser=True).first()

    if not system_user:
        raise RuntimeError("No superuser available for migration.")

    # Minimal DRF-compatible object
    return SimpleNamespace(
        user=system_user,
        POST={},
        FILES=SimpleNamespace(getlist=lambda key: []),
    )


# ------------------------------------------------------------------
# Command
# ------------------------------------------------------------------

class Command(BaseCommand):
    help = "Migrates Helpdesk records to IssueTracker"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and simulate migration without saving.",
        )

    def handle(self, *args, **options):

        dry_run = options["dry_run"]
        request = build_system_request()

        self.stdout.write(self.style.WARNING("Starting Helpdesk → Issue migration"))

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Running in DRY-RUN mode (no data will be saved)")
            )

        self._migrate_bugreports(request, dry_run)
        self._migrate_supporttickets(request, dry_run)

        self.stdout.write(self.style.SUCCESS("Migration completed successfully"))

    # ------------------------------------------------------------------
    # BugReports
    # ------------------------------------------------------------------

    def _migrate_bugreports(self, request, dry_run):

        self.stdout.write("Migrating BugReports...")

        queryset = (
            BugReport.objects
            .filter(migrated_issue_id__isnull=True)
            .iterator()
        )

        for bug in queryset:
            try:
                with transaction.atomic():

                    payload = IssueAdapter.build_bug_issue_payload(bug)

                    serializer = IssueCreateSerializer(
                        data=payload,
                        context={"request": request},
                    )

                    serializer.is_valid(raise_exception=True)

                    if dry_run:
                        self.stdout.write(
                            f"[DRY-RUN] Would migrate BugReport {bug.bug_number}"
                        )
                        continue

                    issue = serializer.save()

                    # -----------------------------
                    # Attachments
                    # -----------------------------
                    files = [a.file for a in bug.attachments.all()]

                    if files:
                        result = IssueMutationService.add_attachments(
                            issue=issue,
                            request=request,
                            files=files,
                        )

                        if not result.success:
                            raise Exception(result.error)

                    bug.migrated_issue_id = issue.id
                    bug.save(update_fields=["migrated_issue_id"])

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Migrated BugReport {bug.bug_number} → Issue {issue.issue_number}"
                        )
                    )

            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(
                        f"Failed to migrate BugReport {bug.id}: {str(exc)}"
                    )
                )

    # ------------------------------------------------------------------
    # SupportTickets
    # ------------------------------------------------------------------

    def _migrate_supporttickets(self, request, dry_run):

        self.stdout.write("Migrating SupportTickets...")

        queryset = (
            SupportTicket.objects
            .filter(migrated_issue_id__isnull=True)
            .iterator()
        )

        for ticket in queryset:
            try:
                with transaction.atomic():

                    payload = IssueAdapter.build_support_issue_payload(ticket)

                    serializer = IssueCreateSerializer(
                        data=payload,
                        context={"request": request},
                    )

                    serializer.is_valid(raise_exception=True)

                    if dry_run:
                        self.stdout.write(
                            f"[DRY-RUN] Would migrate SupportTicket {ticket.ticket_number}"
                        )
                        continue

                    issue = serializer.save()

                    # -----------------------------
                    # Attachments
                    # -----------------------------
                    files = [a.file for a in ticket.attachments.all()]

                    if files:
                        result = IssueMutationService.add_attachments(
                            issue=issue,
                            request=request,
                            files=files,
                        )

                        if not result.success:
                            raise Exception(result.error)

                    ticket.migrated_issue_id = issue.id
                    ticket.save(update_fields=["migrated_issue_id"])

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Migrated SupportTicket {ticket.ticket_number} → Issue {issue.issue_number}"
                        )
                    )

            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(
                        f"Failed to migrate SupportTicket {ticket.id}: {str(exc)}"
                    )
                )
