import logging

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

logger = logging.getLogger(__name__)

class LeaveType(TimeStampedModel, AuditFieldsModel):

    """Model for leave types with default balance."""

    code = models.CharField(max_length=4, unique=True, help_text="Unique leave type code (e.g., 'ANNUAL')")
    name = models.CharField(max_length=100, help_text="Leave type name (e.g., 'Annual Leave')")
    default_balance = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        help_text='Default yearly balance in hours'
    )
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Leave Type"
        verbose_name_plural = "Leave Types"
        indexes = [
            models.Index(fields=['code'], name='leave_type_code_idx'),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        """Validate leave type fields."""
        logger.debug(f"Cleaning LeaveType: code={self.code}")
        if not self.code or not self.name:
            raise ValueError("Code and name are required.")
        if self.default_balance < 0:
            raise ValueError("Default balance cannot be negative.")
        super().clean()

    def save(self, *args, user=None, **kwargs):
        """Save with audit fields."""
        self.clean()
        if user:
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)
        logger.info(f"LeaveType saved: {self}")

    def soft_delete(self, user=None, reason=None):
        """Soft delete leave type."""
        logger.info(f"Soft deleting LeaveType: {self.code}, user={user}")
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(user=user)
