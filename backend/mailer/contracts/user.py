from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EmailUser:

    """
    Immutable data contract for email delivery.

    This contract deliberately avoids any dependency on
    Django ORM, request objects, or domain models.
    """

    id: Optional[int]
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
