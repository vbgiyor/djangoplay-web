import logging
from typing import Any, Optional

from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

class SoftDeleteMixin:

    """Mixin to handle soft delete and restore actions for Django models."""

    def perform_destroy(self, instance: Any, user: Optional[Any] = None) -> None:
        """Perform soft delete on the instance."""
        logger.debug(f"Soft deleting {instance.__class__.__name__}: {instance}, user: {user.id if user else 'None'}")
        try:
            instance.soft_delete(user=user)
            logger.info(f"Successfully soft deleted {instance.__class__.__name__}: {instance}")
        except Exception as e:
            logger.error(f"Error soft deleting {instance.__class__.__name__} {instance}: {str(e)}", exc_info=True)
            raise ValidationError(
                message=f"Failed to soft delete {instance.__class__.__name__.lower()}: {str(e)}",
                code="soft_delete_error"
            )

    def perform_restore(self, instance: Any, user: Optional[Any] = None) -> None:
        """Perform restore on the instance."""
        logger.debug(f"Restoring {instance.__class__.__name__}: {instance}, user: {user.id if user else 'None'}")
        try:
            instance.restore(user=user)
            logger.info(f"Successfully restored {instance.__class__.__name__}: {instance}")
        except Exception as e:
            logger.error(f"Error restoring {instance.__class__.__name__} {instance}: {str(e)}", exc_info=True)
            raise ValidationError(
                message=f"Failed to restore {instance.__class__.__name__.lower()}: {str(e)}",
                code="restore_error"
            )
