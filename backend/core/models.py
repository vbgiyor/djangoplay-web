from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):

    """Abstract base model with timestamp and soft delete fields."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        """Mark instance as deleted with timestamp."""
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        """Restore soft-deleted instance."""
        self.deleted_at = None
        self.save()


class ActiveManager(models.Manager):

    """Manager to filter out soft-deleted records."""

    def get_queryset(self):
        queryset = super().get_queryset().filter(deleted_at__isnull=True)
        # Check if the model has an is_active field
        if hasattr(self.model, 'is_active'):
            queryset = queryset.filter(is_active=True)
        return queryset
