import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from utilities.commons.generate_tokens import generate_secure_token

from users.models import PasswordResetRequest

logger = logging.getLogger(__name__)


class PasswordResetTokenManagerService:
    TOKEN_PREFIX = "pwd_"

    @classmethod
    @transaction.atomic
    def create_for_user(cls, user):
        # Invalidate all existing active tokens
        PasswordResetRequest.objects.filter(
            user=user,
            deleted_at__isnull=True,
            used=False,
        ).update(deleted_at=timezone.now())

        token = generate_secure_token(
            prefix=cls.TOKEN_PREFIX,
            length=64,
        )

        expires_at = timezone.now() + timezone.timedelta(
            days=settings.LINK_EXPIRY_DAYS["password_reset"]
        )

        return PasswordResetRequest.objects.create(
            user=user,
            token=token,
            expires_at=expires_at,
            created_by=user,
        )

    @classmethod
    def validate_token(cls, token: str):
        req = PasswordResetRequest.all_objects.filter(token=token).first()
        if not req:
            return None, "invalid"

        if req.deleted_at or req.used:
            return req, "consumed"

        if req.expires_at < timezone.now():
            return req, "expired"

        return req, "ok"

    @classmethod
    @transaction.atomic
    def consume(cls, req: PasswordResetRequest):
        req.used = True
        req.deleted_at = timezone.now()
        req.save(update_fields=["used", "deleted_at"])
