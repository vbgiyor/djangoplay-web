import logging

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

logger = logging.getLogger(__name__)

class Department(TimeStampedModel, AuditFieldsModel):

    """Model for storing department codes and names."""

    code = models.CharField(max_length=12, unique=True, help_text="Unique department code (e.g., 'FIN')")
    name = models.CharField(max_length=100, help_text="Department name (e.g., 'Finance')")
    history = HistoricalRecords()


    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        indexes = [
            models.Index(fields=['code'], name='department_code_idx'),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        """Validate department fields."""
        logger.debug(f"Cleaning Department: code={self.code}")
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
        logger.info(f"Department saved: {self}")

    def soft_delete(self, user=None, reason=None):
        """Soft delete department."""
        logger.info(f"Soft deleting Department: {self.code}, user={user}")
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.is_active = False
        self.save(user=user)

    def restor(self, user=None):
        """Restore soft deleted department."""
        self.deleted_at = None
        self.deleted_by = None
        self.is_active = True
        self.save(user=user)
