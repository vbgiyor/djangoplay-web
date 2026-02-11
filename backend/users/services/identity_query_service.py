import logging
from typing import TypedDict

from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
UserModel = get_user_model()


class IdentitySnapshot(TypedDict):

    """
    Stable, serializable identity snapshot.

    This is the ONLY identity data external apps are allowed to rely on.
    """

    id: int
    email: str
    is_active: bool
    is_verified: bool


class IdentityQueryService:

    """
    Read-only identity access layer.

    RULES:
    - No writes
    - No HR joins
    - No teamcentral imports
    - No business logic
    """

    @staticmethod
    def get_identity_snapshot(user_id: int) -> IdentitySnapshot:
        """
        Return minimal identity snapshot for a user_id.

        Raises DoesNotExist if user is missing — callers decide behavior.
        """
        user = UserModel.objects.only(
            "id",
            "email",
            "is_active",
            "is_verified",
        ).get(pk=user_id)

        snapshot: IdentitySnapshot = {
            "id": user.id,
            "email": user.email,
            "is_active": bool(user.is_active),
            "is_verified": bool(getattr(user, "is_verified", False)),
        }

        logger.debug(
            "IdentityQueryService.get_identity_snapshot: %s",
            snapshot,
        )

        return snapshot

    @staticmethod
    def is_verified(user_id: int) -> bool:
        """
        Lightweight verification check.
        """
        return UserModel.objects.filter(
            pk=user_id,
            is_verified=True,
            is_active=True,
        ).exists()

    @staticmethod
    def get_by_email(email:str):
        return UserModel.objects.filter(
            email__iexact=email,
            deleted_at__isnull=True,
        ).only("id", "email", "is_active", "is_verified").first()


