import logging

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

logger = logging.getLogger(__name__)


class PasswordResetRequest(TimeStampedModel, AuditFieldsModel):

    """
    Password reset token.

    Invariants:
    - Token is opaque (pwd_*)
    - Only ONE active token per user at a time
    - Older tokens are invalidated eagerly
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_requests",
        help_text="User requesting password reset",
    )

    token = models.CharField(
        max_length=80,
        unique=True,
        db_index=True,
        help_text="Opaque password reset token (pwd_*)",
    )

    expires_at = models.DateTimeField(help_text="Token expiration time")

    # Semantic marker (NOT authoritative)
    used = models.BooleanField(
        default=False,
        help_text="Whether this token was consumed successfully",
    )

    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Password Reset Request"
        verbose_name_plural = "Password Reset Requests"
        indexes = [
            models.Index(fields=["token"], name="password_reset_token_idx"),
            models.Index(fields=["user"], name="password_reset_user_idx"),
        ]

    def __str__(self):
        return f"PasswordResetRequest<{self.user.email}>"


    def clean(self):
        """Validate password reset request fields."""
        logger.debug(f"Cleaning PasswordResetRequest: user={self.user.email}")
        if self.used and self.expires_at < timezone.now():
            raise ValueError("Cannot use expired token.")
        super().clean()

    def save(self, *args, user=None, **kwargs):
        """Save with audit fields."""
        self.clean()
        if user:
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)
        logger.info(f"PasswordResetRequest saved: {self}")

    def soft_delete(self, user=None, reason=None):
        """Soft delete password reset request."""
        logger.info(f"Soft deleting PasswordResetRequest: {self}, user={user}")
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(user=user)
