from dataclasses import dataclass


@dataclass(frozen=True)
class EmailUser:

    """
    Immutable data contract for email delivery.

    This contract deliberately avoids any dependency on
    Django ORM, request objects, or domain models.
    """

    id: int | None
    email: str
    full_name: str | None = None
    is_active: bool = True
