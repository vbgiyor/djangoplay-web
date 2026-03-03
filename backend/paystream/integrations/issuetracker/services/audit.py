"""
IssueTracker → Audit Integration Service
=========================================

Maps IssueTracker lifecycle events
to DjangoPlay AuditEvent entries.

Design:
- No business duplication
- Failure-safe (never break domain logic)
- Deterministic metadata
- Append-only
- No row-level role filtering
- No foreign keys
"""

import logging

from audit.models import AuditEvent

logger = logging.getLogger(__name__)


class IssueTrackerAuditService:

    """
    Integration-layer audit mapper for IssueTracker.
    """

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _actor_payload(identity: dict):
        """
        Convert identity dict to AuditEvent actor fields.
        """
        if not identity:
            return {
                "actor_id": None,
                "actor_type": "anonymous",
                "actor_label": None,
            }

        if identity.get("is_authenticated"):
            return {
                "actor_id": str(identity.get("id")) if identity.get("id") else None,
                "actor_type": "user",
                "actor_label": identity.get("email"),
            }

        return {
            "actor_id": None,
            "actor_type": "anonymous",
            "actor_label": identity.get("email"),
        }

    # ------------------------------------------------------------------
    # Issue Events
    # ------------------------------------------------------------------

    @classmethod
    def log_issue_created(cls, issue, identity):
        try:
            actor = cls._actor_payload(identity)

            AuditEvent.objects.create(
                action="issuetracker.issue_created",
                **actor,
                target_type="Issue",
                target_id=str(issue.id),
                target_label=f"Issue #{issue.issue_number}",
                metadata={
                    "issue_number": issue.issue_number,
                    "title": issue.title,
                    "priority": issue.priority,
                    "is_public": issue.is_public,
                },
                is_system_event=False,
            )

        except Exception:
            logger.exception("Audit log failed (issue_created)")

    @classmethod
    def log_issue_updated(cls, issue, old_data, new_data, identity):
        try:
            actor = cls._actor_payload(identity)

            AuditEvent.objects.create(
                action="issuetracker.issue_updated",
                **actor,
                target_type="Issue",
                target_id=str(issue.id),
                target_label=f"Issue #{issue.issue_number}",
                metadata={
                    "issue_number": issue.issue_number,
                    "old": old_data,
                    "new": new_data,
                    "is_public": issue.is_public,
                },
                is_system_event=False,
            )

        except Exception:
            logger.exception("Audit log failed (issue_updated)")

    @classmethod
    def log_status_change(cls, issue, old_status, new_status, identity):
        try:
            actor = cls._actor_payload(identity)

            AuditEvent.objects.create(
                action="issuetracker.issue_status_changed",
                **actor,
                target_type="Issue",
                target_id=str(issue.id),
                target_label=f"Issue #{issue.issue_number}",
                metadata={
                    "issue_number": issue.issue_number,
                    "old_status": old_status,
                    "new_status": new_status,
                    "is_public": issue.is_public,
                },
                is_system_event=False,
            )

        except Exception:
            logger.exception("Audit log failed (status_change)")

    @classmethod
    def log_issue_deleted(cls, issue, identity):
        try:
            actor = cls._actor_payload(identity)

            AuditEvent.objects.create(
                action="issuetracker.issue_deleted",
                **actor,
                target_type="Issue",
                target_id=str(issue.id),
                target_label=f"Issue #{issue.issue_number}",
                metadata={
                    "issue_number": issue.issue_number,
                    "is_public": issue.is_public,
                },
                is_system_event=False,
            )

        except Exception:
            logger.exception("Audit log failed (issue_deleted)")

    # ------------------------------------------------------------------
    # Comment Events
    # ------------------------------------------------------------------

    @classmethod
    def log_comment_added(cls, issue, comment, identity):
        try:
            actor = cls._actor_payload(identity)

            AuditEvent.objects.create(
                action="issuetracker.comment_added",
                **actor,
                target_type="Comment",
                target_id=str(comment.id),
                target_label=f"Comment on Issue #{issue.issue_number}",
                metadata={
                    "issue_number": issue.issue_number,
                    "comment_id": str(comment.id),
                    "is_public": issue.is_public,
                },
                is_system_event=False,
            )

        except Exception:
            logger.exception("Audit log failed (comment_added)")

    # ------------------------------------------------------------------
    # Attachment Events
    # ------------------------------------------------------------------

    @classmethod
    def log_attachment_uploaded(cls, issue, attachment, identity, comment=None):
        try:
            actor = cls._actor_payload(identity)

            AuditEvent.objects.create(
                action="issuetracker.attachment_uploaded",
                **actor,
                target_type="Attachment",
                target_id=str(attachment.id),
                target_label=attachment.original_name,
                metadata={
                    "issue_number": issue.issue_number,
                    "attachment_id": str(attachment.id),
                    "original_name": attachment.original_name,
                    "size": attachment.size,
                    "comment_id": str(comment.id) if comment else None,
                    "is_public": issue.is_public,
                },
                is_system_event=False,
            )

        except Exception:
            logger.exception("Audit log failed (attachment_uploaded)")

    @classmethod
    def log_attachment_deleted(cls, issue, attachment, identity):
        try:
            actor = cls._actor_payload(identity)

            AuditEvent.objects.create(
                action="issuetracker.attachment_deleted",
                **actor,
                target_type="Attachment",
                target_id=str(attachment.id),
                target_label=attachment.original_name,
                metadata={
                    "issue_number": issue.issue_number,
                    "attachment_id": str(attachment.id),
                    "original_name": attachment.original_name,
                    "is_public": issue.is_public,
                },
                is_system_event=False,
            )

        except Exception:
            logger.exception("Audit log failed (attachment_deleted)")
