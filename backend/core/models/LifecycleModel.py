from audit.signals.events import post_restore, post_soft_delete
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):

    """
    Abstract base model with timestamp, soft delete, and active status fields.

    Design guarantees:
    - Context-tolerant lifecycle methods
    - No audit or domain dependencies
    - Safe for admin, services, signals, and async pipelines
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

    def soft_delete(self, *, user=None, reason=None, **kwargs):
        """
        Soft delete the instance.

        Context parameters are accepted for compatibility with:
        - Admin actions
        - Domain orchestration
        - Audit hooks
        - Future middleware / signals

        This method intentionally does NOT:
        - Record audit events
        - Enforce business rules
        """
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save()

        post_soft_delete.send(
            sender=self.__class__,
            instance=self,
            user=user,
            reason=reason,
        )

    def restore(self, *, user=None, **kwargs):
        """
        Restore a soft-deleted instance.

        Context parameters are accepted for compatibility.
        """
        self.deleted_at = None
        self.is_active = True
        self.save()

        post_restore.send(
            sender=self.__class__,
            instance=self,
            user=user,
        )


class ActiveManager(models.Manager):

    """Manager to filter out soft-deleted and inactive records."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True, is_active=True)
