import logging

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

logger = logging.getLogger(__name__)

class EmploymentStatus(TimeStampedModel, AuditFieldsModel):

    """Model for storing employment status codes and names."""

    code = models.CharField(max_length=4, unique=True, help_text="Unique status code (e.g., 'ACTV')")
    name = models.CharField(max_length=100, help_text="Status name (e.g., 'Active')")
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Employment Status"
        verbose_name_plural = "Employment Statuses"
        indexes = [
            models.Index(fields=['code'], name='employment_status_code_idx'),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        """Validate employment status fields."""
        logger.debug(f"Cleaning EmploymentStatus: code={self.code}")
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
        logger.info(f"EmploymentStatus saved: {self}")

    def soft_delete(self, user=None, reason=None):
        """Soft delete employment status."""
        logger.info(f"Soft deleting EmploymentStatus: {self.code}, user={user}")
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(user=user)
