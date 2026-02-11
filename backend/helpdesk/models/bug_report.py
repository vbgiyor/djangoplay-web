import uuid

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from simple_history.models import HistoricalRecords

from .enums import BugStatus, Severity
from .file_upload import FileUpload


class BugReport(TimeStampedModel, AuditFieldsModel):
    bug_number = models.CharField(max_length=16, unique=True, editable=False)

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bug_reports",
    )

    summary = models.CharField(max_length=255)
    steps_to_reproduce = models.TextField()
    expected_result = models.TextField(blank=True)
    actual_result = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=BugStatus.choices,
        default=BugStatus.NEW,
    )
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.MEDIUM,
    )

    external_issue_url = models.URLField(blank=True)
    emails_sent = models.BooleanField(
        default=False,
        help_text="True if email has been sent",
    )
    attachments = GenericRelation(FileUpload)

    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    def save(self, *args, **kwargs):
        if not self.bug_number:
            self.bug_number = f"B{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)
