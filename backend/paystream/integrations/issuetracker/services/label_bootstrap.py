import logging

from genericissuetracker.models import Label
from paystream.integrations.issuetracker.constants import (
    IssueLabelMeta,
    IssueLabelSlug,
)

logger = logging.getLogger(__name__)


class IssueLabelBootstrapService:

    """
    Ensures required Issue labels exist.

    Idempotent and safe to call multiple times.
    """

    _bootstrapped = False

    @classmethod
    def ensure_labels_exist(cls):

        if cls._bootstrapped:
            return

        labels = [
            {
                "slug": IssueLabelSlug.BUG_INTERNAL,
                "name": IssueLabelMeta.BUG_INTERNAL_NAME,
                "color": "#dc3545",
            },
            {
                "slug": IssueLabelSlug.BUG_PUBLIC,
                "name": IssueLabelMeta.BUG_PUBLIC_NAME,
                "color": "#28a745",
            },
        ]

        for item in labels:
            Label.objects.get_or_create(
                slug=item["slug"],
                defaults={
                    "name": item["name"],
                    "color": item["color"],
                },
            )

        cls._bootstrapped = True

        logger.info("IssueTracker labels ensured.")
