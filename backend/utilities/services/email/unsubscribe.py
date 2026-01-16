import logging

from allauth.account.models import EmailAddress
from django.db import transaction

logger = logging.getLogger(__name__)


class EmailUnsubscribeService:

    """
    Handles unsubscribe and resubscribe email state transitions.

    Important:
    - Does NOT handle business/domain rules
    - Does NOT modify verification semantics
    - Operates strictly on email delivery state

    """

    @staticmethod
    @transaction.atomic
    def resubscribe_user(user):
        """
        Restore email delivery for a previously unsubscribed user.
        """
        if not user:
            return

        logger.info("Resubscribing email delivery for user=%s", user.email)

        update_fields = []

        # 1. Restore preferences
        default_prefs = {
            "newsletters": True,
            "offers": True,
            "updates": True,
        }

        user.preferences = default_prefs
        update_fields.append("preferences")

        # 2. Clear global unsubscribe flags
        if hasattr(user, "is_unsubscribed"):
            user.is_unsubscribed = False
            update_fields.append("is_unsubscribed")

        if hasattr(user, "unsubscribed_at"):
            user.unsubscribed_at = None
            update_fields.append("unsubscribed_at")

        user.save(update_fields=update_fields)

        # 3. Restore EmailAddress delivery flags
        EmailAddress.objects.filter(
            user=user,
            email__iexact=user.email,
        ).update(
            verified=True,
            primary=True,
        )

        logger.info("Email resubscribe completed for user=%s", user.email)
