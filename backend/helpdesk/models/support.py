import uuid

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from .enums import Severity, SupportStatus
from .file_upload import FileUpload


class SupportTicket(TimeStampedModel, AuditFieldsModel):
    ticket_number = models.CharField(max_length=16, unique=True, editable=False)

    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=SupportStatus.choices,
        default=SupportStatus.OPEN,
    )
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        blank=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_tickets",
    )

    client_ip = models.GenericIPAddressField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    emails_sent = models.BooleanField(
        default=False,
        help_text="True if email has been sent",
    )
    attachments = GenericRelation(FileUpload)
    migrated_issue_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
    )

    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = f"S{uuid.uuid4().hex[:12].upper()}"
        if self.status in {SupportStatus.RESOLVED, SupportStatus.CLOSED} and not self.resolved_at:
            self.resolved_at = timezone.now()
        super().save(*args, **kwargs)
