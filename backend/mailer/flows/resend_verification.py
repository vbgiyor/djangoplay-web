import logging

from allauth.account.models import EmailAddress
from core.middleware import thread_local
from django.contrib.auth import get_user_model
from teamcentral.models import MemberProfile
from teamcentral.services import MemberLifecycleService
from users.services.identity_verification_token_service import SignupTokenManagerService

from mailer.flows.member.verification import send_verification_email_task
from mailer.throttling.flow_throttle import allow_flow

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


def resend_verification_for_email_task(
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
        return ResendVerificationResult(
            status="no_user",
            message="No user with that email",
        )

    if getattr(user, "is_verified", False):
        return ResendVerificationResult(
            status="already_verified",
            user=user,
            message="User is already verified.",
        )

    # --------------------------------------------------
    # Rate limiting
    # --------------------------------------------------
    ip_value = client_ip or getattr(thread_local, "client_ip", None)

    allowed, reason, dbg = allow_flow(
        flow="resend_verification",
        user_id=user.pk,
        email=user.email,
        client_ip=ip_value,
        prefer_user_identity=False,
    )

    if not allowed:
        return ResendVerificationResult(
            status="rate_limited",
            user=user,
            message=reason,
        )

    # --------------------------------------------------
    # Token creation / reuse (DELEGATED)
    # --------------------------------------------------
    try:
        signup_request, status = SignupTokenManagerService.create_for_user(
            user=user,
            request=None,
            flow="resend_verification",
        )
    except Exception as exc:
        logger.exception("resend_verification: token creation failed")
        return ResendVerificationResult(
            status="error",
            user=user,
            message=str(exc),
        )

    # 🔑 SUCCESS CASES
    if not signup_request:
        return ResendVerificationResult(
            status=status,
            user=user,
            message=f"Verification token unavailable: {status}",
        )

    # --------------------------------------------------
    # Ensure EmailAddress
    # --------------------------------------------------
    EmailAddress.objects.update_or_create(
        user=user,
        email=user.email.lower(),
        defaults={
            "verified": False,
            "primary": True,
        },
    )

    # --------------------------------------------------
    # Ensure Member
    # --------------------------------------------------
    member = MemberProfile.objects.filter(employee=user).first()
    if not member:
        member = MemberLifecycleService.create_member(
            {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "employee": user,
            },
            created_by=created_by,
        )

    # --------------------------------------------------
    # Queue verification email (ALWAYS on success)
    # --------------------------------------------------
    send_verification_email_task.delay(member.id)

    return ResendVerificationResult(
        status="ok",
        user=user,
        member=member,
        signup_request=signup_request,
        queued=True,
    )
