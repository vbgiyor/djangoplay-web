import logging

from core.models import AuditFieldsModel, TimeStampedModel
from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

logger = logging.getLogger(__name__)

class UserActivityLog(TimeStampedModel, AuditFieldsModel):

    """Model for logging user activities with soft deletion."""

    ACTION_CHOICES = [
        ('SIGN_IN', 'Sign In'),
        ('SIGN_OUT', 'Sign Out'),
        ('SIGN_UP', 'Sign Up'),
        ('VERIFY_EMAIL', 'Verify Email'),
        ('RESET_PASSWORD', 'Reset Password'),
        ('RESTORE_ACCOUNT', 'Restore Account'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activity_logs',
        help_text='User who performed the action'
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        help_text='Type of action performed'
    )
    client_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address of the user'
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'User Activity Log'
        verbose_name_plural = 'User Activity Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action'], name='activity_log_action_idx'),
        ]

    def __str__(self):
        return f"{self.user.get_full_name} - {self.get_action_display()} at {self.created_at}"

    def soft_delete(self, user=None, reason=None):
        """Soft delete activity log."""
        logger.info(f"Soft deleting UserActivityLog: {self}, user={user}")
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()
