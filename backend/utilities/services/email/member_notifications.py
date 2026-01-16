import logging
from typing import Any

from celery import shared_task
from django.conf import settings
from django.urls import reverse
from users.models import Member, SupportTicket
from utilities.admin.url_utils import get_admin_url, get_site_base_url
from utilities.commons import helpers
from utilities.constants.template_registry import TemplateRegistry as T
from utilities.services.email.base import send_email_via_adapter
from utilities.services.links.verification import build_verification_url

logger = logging.getLogger(__name__)


base_url = get_site_base_url()
# ---------------------------------------------------------------------
# Signup / verification flow
# ---------------------------------------------------------------------

@shared_task(bind=True)
def send_successful_signup_email_task(self: Any, member_id: int) -> None:
    """
    Send welcome (signup success) AND verification email to a newly created member.

    Order: [signup_success, verification] so user receives onboarding first.
    Verification template chosen by whether the underlying employee used SSO.
    """
    try:
        member = Member.objects.select_related("employee").get(pk=member_id)
    except Member.DoesNotExist:
        logger.warning(
            "send_successful_signup_email_task: member_id=%s not found", member_id
        )
        return

    try:
        verification_url = build_verification_url(member)
    except Exception as e:
        logger.exception(
            "send_successful_signup_email_task: failed to create verification URL for member=%s: %s",
            member.pk,
            e,
        )
        verification_url = None

    # 1) Welcome email (always)
    try:
        send_email_via_adapter(
            template_prefix=T.EMAIL_SIGNUP_SUCCESS,
            to_email=member.email,
            context={
                "member": member,
                "employee": member.employee,
                "login_url": f"{get_site_base_url()}{reverse('account_login')}",
                "site_name": helpers.get_site_name(),
            },
            user=member.employee,
        )
        logger.info(
            "send_successful_signup_email_task: welcome email queued for member=%s <%s>",
            member.pk,
            member.email,
        )
    except Exception as e:
        logger.exception(
            "send_successful_signup_email_task: failed to queue welcome email for member=%s: %s",
            member.pk,
            e,
        )

    # 2) Verification email — choose template based on employee.sso_provider
    try:
        # Determine provider: treat "EMAIL" (or empty) as manual signup
        prov = getattr(member.employee, "sso_provider", None) or "EMAIL"
        if prov.upper() == "EMAIL":
            verification_prefix = T.EMAIL_VERIFICATION_MANUAL
        else:
            verification_prefix = T.EMAIL_VERIFICATION_SSO

        send_email_via_adapter(
            template_prefix=verification_prefix,
            to_email=member.email,
            context={
                "member": member,
                "employee": member.employee,
                "verification_url": verification_url,
                "login_url": f"{base_url}{reverse('account_login')}",
                "site_name": helpers.get_site_name(),
                "verification_expiry_days": settings.LINK_EXPIRY_DAYS["email_verification"],
            },
            user=member.employee,
        )
        logger.info(
            "send_successful_signup_email_task: verification email queued (prefix=%s) for member=%s <%s>",
            verification_prefix,
            member.pk,
            member.email,
        )
    except Exception as e:
        logger.exception(
            "send_successful_signup_email_task: failed to queue verification email for member=%s: %s",
            member.pk,
            e,
        )


@shared_task(bind=True)
def send_verification_email_task(self: Any, member_id: int) -> None:
    """
    Standalone verification email task (kept for cases where verification is
    sent separately from signup).
    """
    try:
        member = Member.objects.select_related("employee").get(pk=member_id)
    except Member.DoesNotExist:
        logger.warning(
            "send_verification_email_task: member_id=%s not found", member_id
        )
        return

    try:
        verification_url = build_verification_url(member)
    except Exception as e:
        logger.exception(
            "send_verification_email_task: failed to create verification URL for member=%s: %s",
            member.pk,
            e,
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
    Manual / SSO verification (special flow). Kept separate because it uses a
    different verification URL and context shape.
    """
    try:
        member = Member.objects.select_related("employee").get(pk=member_id)
    except Member.DoesNotExist:
        logger.warning(
            "send_manual_verification_email_task: member_id=%s not found", member_id
        )
        return

    try:
        verification_url = build_verification_url(member)
    except Exception as e:
        logger.exception(
            "send_verification_email_task: failed to create verification URL for member=%s: %s",
            member.pk,
            e,
        )
        return

    send_email_via_adapter(
        template_prefix=T.EMAIL_MANUAL_VERIFICATION,
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


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_support_or_bug_email_task(self: Any, ticket_id: int) -> None:
    try:
        ticket = SupportTicket.objects.select_related("employee").prefetch_related("file_uploads").get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        logger.warning("send_support_or_bug_email_task: ticket %s not found", ticket_id)
        return

    if ticket.email and ticket.email.lower().strip() == "redstar@djangoplay.com":
        logger.info("Skipping email for redstar")
        ticket.emails_sent = True
        ticket.save(update_fields=["emails_sent"])
        return

    if getattr(ticket, "emails_sent", False):
        logger.info("Emails already sent for ticket %s", ticket_id)
        return

    file_uploads = ticket.file_uploads.all()
    file_names = [f.file.name.split("/")[-1] for f in file_uploads if f.file]

    base_context = {
        "ticket": ticket,
        "site_name": getattr(settings, "SITE_NAME", "DjangoPlay"),
        "admin_url": get_admin_url(ticket),
        "file_names": file_names,
        "file_count": len(file_uploads),
        "has_attachments": len(file_uploads) > 0,
        "user": ticket.employee,
        "employee_id": ticket.employee.id if ticket.employee else None,
    }

    if ticket.is_bug_report:
        context = base_context | {
            "ticket_number": ticket.ticket_number,
            "subject": ticket.subject,
            "description": ticket.message,
            "github_issue": ticket.github_issue,
            "email": ticket.email,
        }
    else:
        context = base_context  # support ticket uses only ticket object

    # Send both emails (same templates for both types)
    send_email_via_adapter(template_prefix=T.REQUEST_TO_SUPPORT_EMAIL,
                           to_email=settings.DEFAULT_FROM_EMAIL, context=context)
    send_email_via_adapter(template_prefix=T.CONFIRMATION_TO_USER_EMAIL,
                           to_email=ticket.email, context=context, user=ticket.employee)

    ticket.emails_sent = True
    ticket.save(update_fields=["emails_sent"])
    logger.info("Emails sent for ticket %s (bug=%s)", ticket_id, ticket.is_bug_report)

