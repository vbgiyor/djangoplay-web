import logging
from dataclasses import dataclass
from typing import Any, Optional, Type

from core.middleware import thread_local
from django.contrib.auth import get_user_model
from utilities.constants.login import (
    RESET_STATUS_LIMIT,
    RESET_STATUS_NOT_FOUND,
    RESET_STATUS_SUCCESS,
    RESET_STATUS_UNSUBSCRIBED,
)
from mailer.throttling.flow_throttle import allow_flow

logger = logging.getLogger(__name__)
UserModel = get_user_model()


@dataclass
class PasswordResetResult:
    status: str
    user: Optional[Any] = None


class PasswordResetService:

    """
    Canonical password-reset entry point.

    Responsibilities:
      1) Resolve user (email / username)
      2) Apply domain rules (active, verified, unsubscribed)
      3) Rate-limit via allow_flow()
      4) Delegate token + email generation to allauth
    """

    # ------------------------------------------------------------------
    # User resolution
    # ------------------------------------------------------------------
    @staticmethod
    def _find_user(identifier: str, identifier_type: str) -> Optional[Type[Any]]:
        value = (identifier or "").strip()
        if not value or not identifier_type:
            return None

        qs = UserModel.objects.filter(is_active=True)

        # Respect soft-delete if present
        try:
            UserModel._meta.get_field("deleted_at")
            qs = qs.filter(deleted_at__isnull=True)
        except Exception:
            pass

        if identifier_type == "email":
            user = qs.filter(email__iexact=value).first()
        else:
            user = qs.filter(username__iexact=value).first()

        logger.info(
            "PasswordResetService._find_user: identifier=%s type=%s found=%s",
            value,
            identifier_type,
            bool(user),
        )
        return user

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @staticmethod
    def send_reset_link(
        *, identifier: str, identifier_type: str, request
    ) -> PasswordResetResult:
        """
        Called by frontend view.

        Returns one of:
          - success
          - notfound
          - limit
          - unsubscribed
        """
        user = PasswordResetService._find_user(identifier, identifier_type)

        # 1) User not found
        if not user:
            return PasswordResetResult(status=RESET_STATUS_NOT_FOUND)

        # 2) Inactive / soft-deleted
        if not user.is_active or getattr(user, "deleted_at", None) is not None:
            return PasswordResetResult(status=RESET_STATUS_NOT_FOUND)

        # 3) Must be verified
        if not getattr(user, "is_verified", False):
            return PasswordResetResult(status=RESET_STATUS_NOT_FOUND)

        # 4) Unsubscribed
        if getattr(user, "is_unsubscribed", False):
            logger.info(
                "PasswordResetService: blocked (unsubscribed) → %s",
                user.email,
            )
            return PasswordResetResult(
                status=RESET_STATUS_UNSUBSCRIBED,
                user=user,
            )

        # 5) Rate limiting
        ip_value = getattr(
            thread_local,
            "client_ip",
            request.META.get("REMOTE_ADDR"),
        )

        allowed, reason, dbg = allow_flow(
            flow="password_reset",
            user_id=user.pk,
            email=user.email,
            client_ip=ip_value,
            prefer_user_identity=True,
        )

        if not allowed:
            logger.info(
                "PasswordResetService: rate-limited user_id=%s email=%s reason=%s dbg=%s",
                user.pk,
                user.email,
                reason,
                dbg,
            )
            return PasswordResetResult(
                status=RESET_STATUS_LIMIT,
                user=user,
            )

        from utilities.services.email.password_reset import (
            send_password_reset_email_task,
        )

        from users.services.password_reset_token_manager import (
            PasswordResetTokenManagerService,
        )

        reset_req = PasswordResetTokenManagerService.create_for_user(user)

        send_password_reset_email_task.delay(
            user_id=user.pk,
            token=str(reset_req.token),
        )

        return PasswordResetResult(
            status=RESET_STATUS_SUCCESS,
            user=user,
        )

