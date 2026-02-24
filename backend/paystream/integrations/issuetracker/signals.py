"""
IssueTracker → Audit Integration
=================================

Maps IssueTracker domain events to AuditEvent entries.

Design Guarantees:
- No modification to audit app
- No domain coupling
- No foreign keys
- Immutable append-only audit
- Never raises
"""

import logging

from audit.contracts.actor import AuditActor
from audit.contracts.target import AuditTarget
from audit.services.recorder import AuditRecorder
from django.dispatch import receiver
from genericissuetracker.signals import (
    issue_commented,
    issue_created,
    issue_deleted,
    issue_status_changed,
    issue_updated,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------------------

def _build_actor(identity: dict):
    """
    Construct AuditActor from identity snapshot.
    """
    if not identity or not identity.get("is_authenticated"):
        return None

    return AuditActor(
        id=identity.get("id"),
        type="user",
        label=identity.get("email"),
    )


def _record_event(*, action: str, actor, target, metadata: dict):
    """
    Safe audit recording wrapper.
    """
    try:
        AuditRecorder.record(
            action=action,
            actor=actor,
            target=target,
            metadata=metadata,
            is_system_event=actor is None,
        )
    except Exception:
        logger.exception("IssueTracker audit logging failed: %s", action)


# ---------------------------------------------------------------------
# ISSUE CREATED
# ---------------------------------------------------------------------

@receiver(issue_created)
def handle_issue_created(sender, issue, identity, **kwargs):

    actor = _build_actor(identity)

    target = AuditTarget(
        type="issuetracker.Issue",
        id=str(issue.id),
        label=f"Issue #{issue.issue_number}",
    )

    metadata = {
        "issue_number": issue.issue_number,
        "title": issue.title,
        "priority": issue.priority,
        "status": issue.status,
        "is_public": issue.is_public,
        "reporter_email": issue.reporter_email,
        "reporter_user_id": issue.reporter_user_id,
    }

    _record_event(
        action="issue_created",
        actor=actor,
        target=target,
        metadata=metadata,
    )


# ---------------------------------------------------------------------
# STATUS CHANGED
# ---------------------------------------------------------------------

@receiver(issue_status_changed)
def handle_issue_status_changed(
    sender,
    issue,
    old_status,
    new_status,
    identity,
    **kwargs,
):

    actor = _build_actor(identity)

    target = AuditTarget(
        type="issuetracker.Issue",
        id=str(issue.id),
        label=f"Issue #{issue.issue_number}",
    )

    metadata = {
        "issue_number": issue.issue_number,
        "old_status": old_status,
        "new_status": new_status,
        "is_public": issue.is_public,
    }

    _record_event(
        action="issue_status_changed",
        actor=actor,
        target=target,
        metadata=metadata,
    )


# ---------------------------------------------------------------------
# COMMENT ADDED
# ---------------------------------------------------------------------

@receiver(issue_commented)
def handle_issue_commented(sender, issue, comment, identity, **kwargs):

    actor = _build_actor(identity)

    target = AuditTarget(
        type="issuetracker.Comment",
        id=str(comment.id),
        label=f"Comment on Issue #{issue.issue_number}",
    )

    metadata = {
        "issue_number": issue.issue_number,
        "comment_id": str(comment.id),
        "commenter_email": comment.commenter_email,
        "commenter_user_id": comment.commenter_user_id,
        "is_public": issue.is_public,
    }

    _record_event(
        action="issue_commented",
        actor=actor,
        target=target,
        metadata=metadata,
    )

@receiver(issue_updated)
def handle_issue_updated(sender, issue, old_data, new_data, identity, **kwargs):

    actor = _build_actor(identity)

    target = AuditTarget(
        type="issuetracker.Issue",
        id=str(issue.id),
        label=f"Issue #{issue.issue_number}",
    )

    metadata = {
        "issue_number": issue.issue_number,
        "old": old_data,
        "new": new_data,
        "is_public": issue.is_public,
    }

    _record_event(
        action="issue_updated",
        actor=actor,
        target=target,
        metadata=metadata,
    )

@receiver(issue_deleted)
def handle_issue_deleted(sender, issue, identity, **kwargs):

    actor = _build_actor(identity)

    target = AuditTarget(
        type="issuetracker.Issue",
        id=str(issue.id),
        label=f"Issue #{issue.issue_number}",
    )

    metadata = {
        "issue_number": issue.issue_number,
        "is_public": issue.is_public,
    }

    _record_event(
        action="issue_deleted",
        actor=actor,
        target=target,
        metadata=metadata,
    )
