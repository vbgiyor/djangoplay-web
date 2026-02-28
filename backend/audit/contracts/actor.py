from dataclasses import dataclass


@dataclass(frozen=True)
class AuditActor:

    """
    Represents the actor responsible for an audited action.

    This is a contract object — NOT a Django model.

    Examples:
        - Authenticated user
        - Anonymous user
        - System / background job
        - External service

    The audit system never assumes ORM availability.

    """

    id: int | None
    type: str
    label: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
        }
