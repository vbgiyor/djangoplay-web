# users/models/signup_request.py

import logging

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

logger = logging.getLogger(__name__)


class SignUpRequest(TimeStampedModel, AuditFieldsModel):

    """
    A single opaque verification token entry for a user's signup.
    Only one active token should exist at a time (enforced in services).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="signup_requests"
    )

    sso_provider = models.CharField(
        max_length=20,
        choices=[
            ('GOOGLE', 'Google'),
            ('APPLE', 'Apple'),
            ('EMAIL', 'Email'),
        ],
        default="EMAIL",
    )

    sso_id = models.CharField(max_length=100, blank=True, null=True)

    # Final token format: vrf_<64 hex chars>
    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Opaque email verification token"
    )

    expires_at = models.DateTimeField(help_text="Expiration timestamp")

    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        indexes = [
            models.Index(fields=["user"], name="signup_request_user_idx"),
            models.Index(fields=["token"], name="signup_request_token_idx"),
        ]

    def __str__(self):
        return f"SignUpRequest<{self.user.email}>"

    # ----------------------------------
    # Proper clean()
    # ----------------------------------
    def clean(self):
        super().clean()

        # Enforce max quota during creation
        from django.conf import settings
        from django.core.exceptions import ValidationError

        qs = SignUpRequest.objects.filter(
            user=self.user,
            deleted_at__isnull=True
        )

        if self.pk:
            qs = qs.exclude(pk=self.pk)

        max_allowed = int(getattr(settings, "SIGNUP_REQUEST_MAX_PER_USER", 1))
        if qs.count() >= max_allowed:
            raise ValidationError(
                {"user": f"Maximum {max_allowed} signup requests allowed per user."}
            )

    # ----------------------------------
    # Override save for audit fields
    # ----------------------------------
    def save(self, *args, user=None, **kwargs):
        self.clean()
        if user:
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)
        logger.info(f"SignUpRequest saved: {self}")
