from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):

    """Abstract base model with timestamp, soft delete, and active status fields."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        """Mark instance as deleted with timestamp."""
        self.deleted_at = timezone.now()
        self.is_active = False  # Also mark as inactive on soft delete
        self.save()

    def restore(self):
        """Restore soft-deleted instance."""
        self.deleted_at = None
        self.is_active = True  # Restore active status
        self.save()


class ActiveManager(models.Manager):

    """Manager to filter out soft-deleted and inactive records."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True, is_active=True)
