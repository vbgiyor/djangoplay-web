import logging

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

logger = logging.getLogger(__name__)

class Role(TimeStampedModel, AuditFieldsModel):

    """Model for storing role codes, titles, and hierarchy."""

    code = models.CharField(max_length=4, unique=True, help_text="Unique role code (e.g., 'CEO')")
    title = models.CharField(max_length=100, help_text="Role title (e.g., 'Chief Executive Officer')")
    rank = models.PositiveIntegerField(default=0, help_text="Hierarchy rank (lower is higher rank)")
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        indexes = [
            models.Index(fields=['code'], name='role_code_idx'),
            models.Index(fields=['rank'], name='role_rank_idx'),
        ]

    def __str__(self):
        return f"{self.title} ({self.code})"

    def clean(self):
        """Validate role fields."""
        logger.debug(f"Cleaning Role: code={self.code}")
        if not self.code or not self.title:
            raise ValueError("Code and title are required.")
        super().clean()

    def save(self, *args, user=None, **kwargs):
        """Save with audit fields."""
        self.clean()
        if user:
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)
        logger.info(f"Role saved: {self}")

    def soft_delete(self, user=None, reason=None):
        """Soft delete role."""
        logger.info(f"Soft deleting Role: {self.code}, user={user}")
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(user=user)
