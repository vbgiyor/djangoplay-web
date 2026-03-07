from typing import Any


class IssueAdapter:

    """
    Adapter translating Helpdesk entities into IssueTracker payloads.
    Keeps Helpdesk services decoupled from IssueTracker implementation.
    """

    BUG_LABEL = "bug"
    SUPPORT_LABEL = "support"

    BUG_STATUS_MAP = {
        "NEW": "OPEN",
        "TRIAGED": "OPEN",
        "IN_PROGRESS": "IN_PROGRESS",
        "FIXED": "RESOLVED",
        "VERIFIED": "RESOLVED",
        "CLOSED": "CLOSED",
    }

    SUPPORT_STATUS_MAP = {
        "OPEN": "OPEN",
        "IN_PROGRESS": "IN_PROGRESS",
        "RESOLVED": "RESOLVED",
        "CLOSED": "CLOSED",
    }

    @staticmethod
    def build_bug_issue_payload(bug, reporter_user_id=None) -> dict[str, Any]:
        """
        Convert BugReport → Issue payload
        """
        description_parts = []

        if bug.steps_to_reproduce:
            description_parts.append(
                f"### Steps to Reproduce\n{bug.steps_to_reproduce}"
            )

        if bug.expected_result:
            description_parts.append(
                f"### Expected Result\n{bug.expected_result}"
            )

        if bug.actual_result:
            description_parts.append(
                f"### Actual Result\n{bug.actual_result}"
            )

        description = "\n\n".join(description_parts) or bug.summary

        return {
            "title": bug.summary,
            "description": description,
            "reporter_email": getattr(bug.reporter, "email", None),
            "reporter_user_id": reporter_user_id,
            "priority": bug.severity,
            "status": IssueAdapter.BUG_STATUS_MAP.get(bug.status, "OPEN"),
            "is_public": True,
            "labels": [IssueAdapter.BUG_LABEL],
            "metadata": {
                "source": "bug_report",
                "legacy_bug_number": bug.bug_number,
            },
        }

    @staticmethod
    def build_support_issue_payload(ticket, reporter_user_id=None) -> dict[str, Any]:
        """
        Convert SupportTicket → Issue payload
        """
        from helpdesk.models.enums import Severity
        # Normalize severity
        severity = ticket.severity.strip() if ticket.severity else None

        if severity in Severity.values:
            priority = severity
        else:
            # Default fallback for legacy blank severity
            priority = Severity.MEDIUM

        return {
            "title": ticket.subject,
            "description": ticket.message,
            "reporter_email": ticket.email,
            "reporter_user_id": reporter_user_id,
            "priority": priority,
            "status": IssueAdapter.SUPPORT_STATUS_MAP.get(ticket.status, "OPEN"),
            "is_public": True,
            "labels": [IssueAdapter.SUPPORT_LABEL],
            "metadata": {
                "source": "support_ticket",
                "legacy_ticket_number": ticket.ticket_number,
            },
        }
