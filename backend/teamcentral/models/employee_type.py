import logging

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

logger = logging.getLogger(__name__)

class EmployeeType(TimeStampedModel, AuditFieldsModel):

    """Model for storing employee type codes and names."""

    code = models.CharField(max_length=4, unique=True, help_text="Unique type code (e.g., 'FT')")
    name = models.CharField(max_length=100, help_text="Type name (e.g., 'Full-Time')")
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Employee Type"
        verbose_name_plural = "Employee Types"
        indexes = [
            models.Index(fields=['code'], name='employee_type_code_idx'),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        """Validate employee type fields."""
        logger.debug(f"Cleaning EmployeeType: code={self.code}")
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
        logger.info(f"EmployeeType saved: {self}")

    def soft_delete(self, user=None, reason=None):
        """Soft delete employee type."""
        logger.info(f"Soft deleting EmployeeType: {self.code}, user={user}")
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(user=user)
