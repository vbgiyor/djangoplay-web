import logging
from typing import Any

from celery import shared_task
from django.conf import settings
from django.urls import reverse
from teamcentral.models import MemberProfile
from users.services.identity_verification_token_service import (
    SignupTokenManagerService,
)
from utilities.admin.url_utils import get_site_base_url
from utilities.commons import helpers
from utilities.constants.template_registry import TemplateRegistry as T

from mailer.engine.base import send_email_via_adapter
from mailer.links.verification import build_verification_url

logger = logging.getLogger(__name__)
base_url = get_site_base_url()


@shared_task(bind=True)
def send_successful_signup_email_task(self: Any, member_id: int) -> None:
    """
    Send welcome (signup success) AND verification email to a newly created member.

    Order:
      1) Welcome email
      2) Verification email (manual vs SSO)

    Important:
    - No users.models imports
    - SignupRequest access ONLY via SignupTokenManagerService

    """
    try:
        member = MemberProfile.objects.select_related("employee").get(pk=member_id)
    except MemberProfile.DoesNotExist:
        logger.warning(
            "send_successful_signup_email_task: member_id=%s not found",
            member_id,
        )
        return

    # --------------------------------------------------
    # Build verification URL (via identity service)
    # --------------------------------------------------
    try:
        signup_request = SignupTokenManagerService.get_latest_active_request(
            user=member.employee
        )

        if not signup_request:
            logger.error(
                "send_successful_signup_email_task: no active signup_request "
                "user_id=%s member_id=%s",
                member.employee_id,
                member.pk,
            )
            verification_url = None
        else:
            verification_url = build_verification_url(
                member=member,
                signup_request=signup_request,
            )

    except Exception as exc:
        logger.exception(
            "send_successful_signup_email_task: failed to build verification URL "
            "member=%s: %s",
            member.pk,
            exc,
        )
        verification_url = None

    # --------------------------------------------------
    # 1) Welcome email
    # --------------------------------------------------
    try:
        send_email_via_adapter(
            template_prefix=T.EMAIL_SIGNUP_SUCCESS,
            to_email=member.email,
            context={
                "member": member,
                "employee": member.employee,
                "login_url": f"{base_url}{reverse('account_login')}",
                "site_name": helpers.get_site_name(),
            },
            user=member.employee,
        )
        logger.info(
            "send_successful_signup_email_task: welcome email queued "
            "member=%s <%s>",
            member.pk,
            member.email,
        )
    except Exception as exc:
        logger.exception(
            "send_successful_signup_email_task: welcome email failed "
            "member=%s: %s",
            member.pk,
            exc,
        )

    # --------------------------------------------------
    # 2) Verification email (manual vs SSO)
    # --------------------------------------------------
    try:
        provider = getattr(member.employee, "sso_provider", None) or "EMAIL"
        verification_prefix = (
            T.EMAIL_VERIFICATION_MANUAL
            if provider.upper() == "EMAIL"
            else T.EMAIL_VERIFICATION_SSO
        )

        send_email_via_adapter(
            template_prefix=verification_prefix,
            to_email=member.email,
            context={
                "member": member,
                "employee": member.employee,
                "verification_url": verification_url,
                "login_url": f"{base_url}{reverse('account_login')}",
                "site_name": helpers.get_site_name(),
                "verification_expiry_days": settings.LINK_EXPIRY_DAYS[
                    "email_verification"
                ],
            },
            user=member.employee,
        )

        logger.info(
            "send_successful_signup_email_task: verification email queued "
            "(prefix=%s) member=%s <%s>",
            verification_prefix,
            member.pk,
            member.email,
        )

    except Exception as exc:
        logger.exception(
            "send_successful_signup_email_task: verification email failed "
            "member=%s: %s",
            member.pk,
            exc,
        )
