from typing import Optional
from mailer.contracts.user import EmailUser


def to_email_user(user) -> Optional[EmailUser]:
    """
    Convert a Django user-like object to EmailUser.
    Adapter helpers for converting domain models into mailer contracts.

    NOTE:
    These adapters exist to support future decoupling of 
    mailer from ORM models.
    """
    if user is None:
        return None

    return EmailUser(
        id=getattr(user, "id", None),
        email=getattr(user, "email", None),
        full_name=(
            user.get_full_name
            if hasattr(user, "get_full_name")
            else None
        ),
        is_active=getattr(user, "is_active", True),
    )
