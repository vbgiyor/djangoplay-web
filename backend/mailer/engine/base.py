import logging
import smtplib
import socket
from typing import Any, Dict, Optional

from allauth.account.adapter import get_adapter

logger = logging.getLogger(__name__)


def send_email_via_adapter(
    *,
    template_prefix: str,
    to_email: str,
    context: Optional[Dict[str, Any]] = None,
    user: Optional[Any] = None,
    request: Optional[Any] = None,
):
    """
    Generic helper used by all email Celery tasks.

    - Uses your CustomAccountAdapter under the hood.
    - Returns the EmailMultiAlternatives message instance on success.
    - Returns None if sending fails (e.g., no internet, SMTP down).
    """
    context = context or {}

    if not to_email:
        logger.warning(
            "send_email_via_adapter called without to_email. "
            "template_prefix=%s",
            template_prefix,
        )
        return None

    adapter = get_adapter()
    adapter.request = None

    if user and "user" not in context:
        context = {**context, "user": user}

    try:
        msg = adapter.send_mail(template_prefix, to_email, context)
        if msg:
            logger.info(
                "send_email_via_adapter: email sent template_prefix=%s → %s",
                template_prefix,
                to_email,
            )
        else:
            logger.warning(
                "send_email_via_adapter: adapter did not send email "
                "template_prefix=%s → %s",
                template_prefix,
                to_email,
            )
        return msg

    except (socket.gaierror, smtplib.SMTPException, OSError) as e:
        logger.warning(
            "send_email_via_adapter: network/SMTP error for "
            "template_prefix=%s → %s: %s",
            template_prefix,
            to_email,
            e,
        )
        return None

    except Exception:
        logger.exception(
            "send_email_via_adapter: unexpected error for "
            "template_prefix=%s → %s",
            template_prefix,
            to_email,
        )
        raise
