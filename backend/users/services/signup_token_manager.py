import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from allauth.account.models import EmailAddress
from core.middleware import thread_local
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from mailer.throttling.flow_throttle import allow_flow
from utilities.commons.generate_tokens import generate_secure_token

from users.models import (
    Employee,
    EmploymentStatus,
    Member,
    MemberStatus,
    SignUpRequest,
)

logger = logging.getLogger(__name__)


@dataclass
class TokenValidationResult:
    ok: bool
    user: Optional[Employee] = None
    member: Optional[Member] = None
    reason: Optional[str] = None
    signup_request: Optional[SignUpRequest] = None


class SignupTokenManagerService:

    """
    Canonical verification token manager.

    CONTRACT:
    - Token validation is stateless and login-agnostic
    - Ownership is resolved ONLY from the token
    - Consumed tokens are idempotent
    """

    TOKEN_PREFIX = "vrf_"

    # ------------------------------------------------------------------
    # CREATE TOKEN
    # ------------------------------------------------------------------
    @classmethod
    @transaction.atomic
    def create_for_user(
        cls,
        user: Employee,
        request=None
    ) -> Tuple[Optional[SignUpRequest], str]:

        client_ip = getattr(thread_local, "client_ip", None) or (
            request.META.get("REMOTE_ADDR") if request else None
        )

        allowed, reason, _ = allow_flow(
            flow="resend_verification",
            user_id=user.pk,
            email=user.email,
            client_ip=client_ip,
        )

        if not allowed:
            return None, "rate_limited"

        # Invalidate any existing active tokens
        SignUpRequest.objects.filter(
            user=user,
            deleted_at__isnull=True,
        ).update(deleted_at=timezone.now())

        token = generate_secure_token(
            prefix=cls.TOKEN_PREFIX,
            length=60,
        )

        expires_at = timezone.now() + timezone.timedelta(
            days=settings.LINK_EXPIRY_DAYS["email_verification"]
        )

        req = SignUpRequest.objects.create(
            user=user,
            token=token,
            expires_at=expires_at,
            created_by=user,
        )

        logger.info(
            "Created verification token for %s token=%s",
            user.email,
            token,
        )

        return req, "ok"

    # ------------------------------------------------------------------
    # RESEND
    # ------------------------------------------------------------------
    @classmethod
    def resend_for_email(cls, email: str, request=None) -> str:
        user = Employee.objects.filter(
            email__iexact=email,
            deleted_at__isnull=True,
        ).first()

        if not user:
            return "no_user"

        if user.is_verified:
            return "already_verified"

        signup_request, status = cls.create_for_user(user, request)
        if status != "ok":
            return status

        from mailer.flows.member.verification import send_verification_email_task

        member = Member.objects.filter(employee=user).first()
        if member:
            send_verification_email_task.delay(member.id)

        return "ok"

    # ------------------------------------------------------------------
    # VALIDATE TOKEN (PURE)
    # ------------------------------------------------------------------
    @classmethod
    def validate_token(cls, token: str) -> TokenValidationResult:
        """
        Validate verification token.

        Rules:
        - Token existence defines ownership
        - Consumed tokens are idempotent
        - Login/session state is irrelevant
        """
        if not token or not token.startswith(cls.TOKEN_PREFIX):
            return TokenValidationResult(
                ok=False,
                reason="invalid",
            )

        # req = SignUpRequest.objects.filter(token=token).first()
        req = SignUpRequest.all_objects.filter(token=token).first()
        if not req:
            return TokenValidationResult(
                ok=False,
                reason="invalid",
            )

        if req.deleted_at is not None:
            return TokenValidationResult(
                ok=False,
                reason="consumed",
                user=req.user,
            )

        if req.expires_at < timezone.now():
            return TokenValidationResult(
                ok=False,
                reason="expired",
                user=req.user,
            )

        member = Member.objects.filter(
            employee=req.user,
            deleted_at__isnull=True,
        ).first()

        return TokenValidationResult(
            ok=True,
            user=req.user,
            member=member,
            signup_request=req,
        )

    # ------------------------------------------------------------------
    # CONSUME + ACTIVATE
    # ------------------------------------------------------------------
    @classmethod
    @transaction.atomic
    def consume_and_activate(cls, signup_request: SignUpRequest):
        user = signup_request.user

        SignUpRequest.objects.filter(
            user=user,
            deleted_at__isnull=True,
        ).update(deleted_at=timezone.now())

        EmailAddress.objects.update_or_create(
            user=user,
            email=user.email,
            defaults={
                "verified": True,
                "primary": True,
            },
        )

        user.is_verified = True
        user.employment_status = EmploymentStatus.objects.get(code="ACTV")
        user.save()

        member = Member.objects.filter(employee=user).first()
        if member:
            member.status = MemberStatus.objects.get(code="ACTV")
            member.save(user=user)

        return True
