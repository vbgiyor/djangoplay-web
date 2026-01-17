import logging

from django.dispatch import receiver

from audit.contracts.actor import AuditActor
from audit.contracts.target import AuditTarget
from audit.services.recorder import AuditRecorder
from audit.signals.events import post_restore, post_soft_delete

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# SOFT DELETE SIGNAL
# ---------------------------------------------------------------------
@receiver(post_soft_delete)
def audit_post_soft_delete(sender, instance, **kwargs):
    """
    Record audit event AFTER a model is soft-deleted.

    This handler:
    - Observes only
    - Never mutates domain models
    - Never raises
    """
    try:
        _record_lifecycle_event(
            action="deleted",
            instance=instance,
        )
    except Exception:
        logger.exception(
            "audit_post_soft_delete failed",
            extra={
                "model": sender.__name__,
                "pk": getattr(instance, "pk", None),
            },
        )


# ---------------------------------------------------------------------
# RESTORE SIGNAL
# ---------------------------------------------------------------------
@receiver(post_restore)
def audit_post_restore(sender, instance, **kwargs):
    """
    Record audit event AFTER a model is restored.

    This handler:
    - Observes only
    - Never mutates domain models
    - Never raises
    """
    try:
        _record_lifecycle_event(
            action="restored",
            instance=instance,
        )
    except Exception:
        logger.exception(
            "audit_post_restore failed",
            extra={
                "model": sender.__name__,
                "pk": getattr(instance, "pk", None),
            },
        )


# ---------------------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------------------
def _record_lifecycle_event(*, action: str, instance):
    """
    Record a lifecycle audit event using canonical contracts.
    """
    # -------------------------------
    # ACTOR
    # -------------------------------
    actor = None
    deleted_by = getattr(instance, "deleted_by", None)

    if deleted_by:
        actor = AuditActor(
            id=getattr(deleted_by, "pk", None),
            type="user",
            label=getattr(deleted_by, "email", None),
        )

    # -------------------------------
    # TARGET
    # -------------------------------
    target = AuditTarget(
        type=f"{instance._meta.app_label}.{instance.__class__.__name__}",
        id=instance.pk,
        label=str(instance),
    )

    # -------------------------------
    # RECORD
    # -------------------------------
    AuditRecorder.record(
        action=action,
        actor=actor,
        target=target,
        metadata={
            "model": instance.__class__.__name__,
            "app": instance._meta.app_label,
        },
        is_system_event=actor is None,
    )

