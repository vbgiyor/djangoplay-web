from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class TimelineEvent:

    type: str
    timestamp: datetime
    actor_email: str | None
    payload: dict[str, Any]


class IssueTimelineService:

    @staticmethod
    def build(issue):

        events = []

        # -------------------------------------------------
        # Status transitions
        # -------------------------------------------------
        for h in issue.status_history.all():

            events.append(
                TimelineEvent(
                    type=h.event_type or "status_changed",
                    timestamp=h.created_at,
                    actor_email=h.changed_by_email,
                    payload={
                        "old_status": h.old_status,
                        "new_status": h.new_status,
                        "metadata": h.metadata or {},
                    },
                )
            )

        # -------------------------------------------------
        # Comments
        # -------------------------------------------------
        for c in issue.comments.all():

            attachments = list(c.attachments.all())

            events.append(
                TimelineEvent(
                    type="comment_added",
                    timestamp=c.created_at,
                    actor_email=c.commenter_email,
                    payload={
                        "body": c.body,
                        "comment_id": c.id,
                        "attachments": [
                            {
                                "file_name": a.original_name,
                                "attachment_number": a.number,
                            }
                            for a in attachments
                        ],
                    },
                )
            )

        # -------------------------------------------------
        # Attachments
        # -------------------------------------------------
        for a in issue.attachments.filter(comment__isnull=True):

            events.append(
                TimelineEvent(
                    type="attachment_added",
                    timestamp=a.created_at,
                    actor_email=a.uploaded_by_email,
                    payload={
                        "file_name": a.original_name,
                        "attachment_number": a.number,
                    },
                )
            )

        return sorted(events, key=lambda e: e.timestamp, reverse=True)
