import logging

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

logger = logging.getLogger(__name__)

class MemberStatus(TimeStampedModel, AuditFieldsModel):

    """Model for storing member status codes and names."""

    code = models.CharField(max_length=4, unique=True, help_text="Unique status code (e.g., 'ACTV')")
    name = models.CharField(max_length=100, help_text="Status name (e.g., 'Active')")
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Member Status"
        verbose_name_plural = "Member Statuses"
        indexes = [
            models.Index(fields=['code'], name='member_status_code_idx'),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        """Validate member status fields."""
        logger.debug(f"Cleaning MemberStatus: code={self.code}")
        if not self.code or not self.name:
            raise ValueError("Code and name are required.")
        super().clean()

    def save(self, *args, user=None, **kwargs):
        """Save with audit fields."""
        self.clean()
        if user:
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)
        logger.info(f"MemberStatus saved: {self}")

    def soft_delete(self, user=None, reason=None):
        """Soft delete member status."""
        logger.info(f"Soft deleting MemberStatus: {self.code}, user={user}")
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(user=user)
