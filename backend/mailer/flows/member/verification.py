import logging
from typing import Any

from celery import shared_task
from teamcentral.models import MemberProfile
from users.services.identity_verification_token_service import (
    SignupTokenManagerService,
)
from utilities.commons import helpers
from utilities.constants.template_registry import TemplateRegistry as T

from mailer.engine.base import send_email_via_adapter
from mailer.links.verification import build_verification_url

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def send_verification_email_task(self: Any, member_id: int) -> None:
    """
    Send verification email for an existing member.

    RULES:
    - No users.models imports
    - SignupRequest access ONLY via SignupTokenManagerService
    """
    try:
        member = MemberProfile.objects.select_related("employee").get(pk=member_id)
    except MemberProfile.DoesNotExist:
        logger.warning(
            "send_verification_email_task: member_id=%s not found",
            member_id,
        )
        return

    try:
        signup_request = SignupTokenManagerService.get_latest_active_request(
            user=member.employee
        )

        if not signup_request:
            logger.error(
                "send_verification_email_task: no active signup_request "
                "user_id=%s member_id=%s",
                member.employee_id,
                member.pk,
            )
            return

        verification_url = build_verification_url(
            member=member,
            signup_request=signup_request,
        )

    except Exception as exc:
        logger.exception(
            "send_verification_email_task: failed to build verification URL "
            "member=%s: %s",
            member.pk,
            exc,
        )
        return

    send_email_via_adapter(
        template_prefix=T.EMAIL_VERIFICATION_MANUAL,
        to_email=member.email,
        context={
            "member": member,
            "employee": member.employee,
            "verification_url": verification_url,
            "site_name": helpers.get_site_name(),
        },
        user=member.employee,
    )


@shared_task(bind=True)
def send_manual_verification_email_task(
    self: Any,
    member_id: int,
    username: str,
    first_name: str,
    last_name: str,
) -> None:
    """
    Manual / SSO verification email flow.

    RULES:
    - No users.models imports
    - Token resolution via identity service only
    """
    try:
        member = MemberProfile.objects.select_related("employee").get(pk=member_id)
    except MemberProfile.DoesNotExist:
        logger.warning(
            "send_manual_verification_email_task: member_id=%s not found",
            member_id,
        )
        return

    try:
        signup_request = SignupTokenManagerService.get_latest_active_request(
            user=member.employee
        )

        if not signup_request:
            logger.error(
                "send_manual_verification_email_task: no active signup_request "
                "user_id=%s member_id=%s",
                member.employee_id,
                member.pk,
            )
            return

        verification_url = build_verification_url(
            member=member,
            signup_request=signup_request,
        )

    except Exception as exc:
        logger.exception(
            "send_manual_verification_email_task: failed to build verification URL "
            "member=%s: %s",
            member.pk,
            exc,
        )
        return

    send_email_via_adapter(
        template_prefix=T.EMAIL_VERIFICATION_MANUAL,
        to_email=member.email,
        context={
            "member": member,
            "verification_url": verification_url,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "site_name": helpers.get_site_name(),
        },
        user=member.employee,
    )
