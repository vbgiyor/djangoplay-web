import logging

from allauth.account.models import EmailAddress
from core.middleware import thread_local
from django.contrib.auth import get_user_model
from users.models import Member
from users.services.member import MemberService
from users.services.signup_token_manager import SignupTokenManagerService
from utilities.services.email.flow_throttle import allow_flow
from utilities.services.email.member_notifications import send_verification_email_task

logger = logging.getLogger(__name__)
User = get_user_model()


class ResendVerificationResult:
    def __init__(
        self,
        status: str,
        user=None,
        member=None,
        signup_request=None,
        queued=False,
        message=None,
    ):
        self.status = status              # ok | already_verified | no_user | rate_limited | error
        self.user = user
        self.member = member
        self.signup_request = signup_request
        self.queued = queued
        self.message = message


def resend_verification_for_email(
    email: str,
    created_by=None,
    client_ip: str | None = None,
) -> ResendVerificationResult:
    """
    Resend verification email for an existing (unverified) user.

    Responsibilities:
    - rate limiting
    - ensure EmailAddress exists
    - ensure Member exists
    - delegate token creation
    - queue verification email

    Token lifecycle is owned by SignupTokenManagerService.
    """
    if not email:
        return ResendVerificationResult(
            status="no_user",
            message="Empty email",
        )

    try:
        user = User.all_objects.get(email__iexact=email)
    except User.DoesNotExist:
        logger.info("resend_verification: no user for email=%s", email)
        return ResendVerificationResult(
            status="no_user",
            message="No user with that email",
        )

    if getattr(user, "is_verified", False):
        logger.info("resend_verification: user already verified: %s", email)
        return ResendVerificationResult(
            status="already_verified",
            user=user,
            message="User is already verified.",
        )


    # ------------------------------------------------------------------
    # Rate limiting (client_ip + email)
    # ------------------------------------------------------------------
    ip_value = client_ip or getattr(thread_local, "client_ip", None)

    allowed, reason, dbg = allow_flow(
        flow="resend_verification",
        user_id=user.pk,
        email=user.email,
        client_ip=ip_value,
        prefer_user_identity=False,   # resend prefers email identity
    )

    if not allowed:
        logger.info(
            "resend_verification blocked: reason=%s debug=%s",
            reason,
            dbg,
        )
        return ResendVerificationResult(
            status="rate_limited",
            user=user,
            message=reason,
        )

    # ------------------------------------------------------------------
    # Token creation (DELEGATED)
    # ------------------------------------------------------------------
    try:
        signup_request, status = SignupTokenManagerService.create_for_user(
            user=user,
            request=None,
        )
    except Exception as exc:
        logger.exception(
            "resend_verification: token creation failed for %s: %s",
            email,
            exc,
        )
        return ResendVerificationResult(
            status="error",
            user=user,
            message=str(exc),
        )

    if status != "ok":
        return ResendVerificationResult(
            status=status,
            user=user,
            message=f"Verification token creation failed: {status}",
        )

    # ------------------------------------------------------------------
    # EmailAddress (ensure primary + unverified)
    # ------------------------------------------------------------------
    try:
        EmailAddress.objects.update_or_create(
            user=user,
            email=user.email.lower(),
            defaults={
                "verified": False,
                "primary": True,
            },
        )
    except Exception as exc:
        logger.exception(
            "resend_verification: EmailAddress update failed for %s: %s",
            email,
            exc,
        )
        return ResendVerificationResult(
            status="error",
            user=user,
            signup_request=signup_request,
            message=str(exc),
        )

    # ------------------------------------------------------------------
    # Member (ensure exists)
    # ------------------------------------------------------------------
    try:
        member = Member.objects.filter(employee=user).first()
        if not member:
            member = MemberService.create_member(
                {
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "employee": user,
                },
                created_by=created_by,
            )
            logger.info(
                "resend_verification: created Member for user=%s member_id=%s",
                user.pk,
                member.pk,
            )
    except Exception as exc:
        logger.exception(
            "resend_verification: member creation failed for %s: %s",
            email,
            exc,
        )
        return ResendVerificationResult(
            status="error",
            user=user,
            signup_request=signup_request,
            message=str(exc),
        )

    # ------------------------------------------------------------------
    # Queue verification email
    # ------------------------------------------------------------------
    try:
        send_verification_email_task.delay(member.id)
        logger.info(
            "resend_verification: queued verification email for member=%s",
            member.pk,
        )
        return ResendVerificationResult(
            status="ok",
            user=user,
            member=member,
            signup_request=signup_request,
            queued=True,
        )
    except Exception as exc:
        logger.exception(
            "resend_verification: failed to queue email for member=%s: %s",
            member.pk,
            exc,
        )
        return ResendVerificationResult(
            status="error",
            user=user,
            member=member,
            signup_request=signup_request,
            message=str(exc),
        )
