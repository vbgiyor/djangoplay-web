from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AuditTarget:

    """
    Represents the target of an audited action.

    This is a contract object — NOT a Django model.

    Examples:
        - support_ticket
        - bug_report
        - invoice
        - client
        - location
        - authentication_session

    """

    type: str
    id: Optional[int]
    label: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "id": self.id,
            "label": self.label,
        }
