import logging
from typing import Any, Dict, Optional

from core.request_context import client_ip, request_id
from django.utils import timezone

from audit.models.audit_event import AuditEvent
from audit.services.normalizer import normalize_actor, normalize_target

logger = logging.getLogger(__name__)


class AuditRecorder:

    """
    Central audit write service.

    Design guarantees:
    - Never raises
    - Never blocks business logic
    - Never imports domain models
    - Safe for sync, async, and background execution
    """

    @staticmethod
    def record(
        *,
        action: str,
        actor=None,
        target=None,
        metadata: Optional[Dict[str, Any]] = None,
        is_system_event: bool = False,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Record an immutable audit event.
        """
        if not action:
            logger.warning("AuditRecorder.record called without action")
            return

        try:
            actor_data = normalize_actor(actor)
            target_data = normalize_target(target)

            AuditEvent.objects.create(
                occurred_at=timezone.now(),
                action=action,
                request_id=request_id.get(),
                client_ip=client_ip.get(),
                user_agent=user_agent,
                is_system_event=is_system_event,
                metadata=metadata or {},
                **actor_data,
                **target_data,
            )
            logger.info(
                "Audit event recorded",
                extra={
                    "action": action,
                    "actor": actor_data,
                    "target": target_data,
                    "request_id": request_id.get(),
                },
            )

        except Exception as exc:
            # ABSOLUTE RULE: auditing must never break runtime
            logger.error(
                "AuditRecorder failed (action=%s)",
                action,
                exc_info=exc,
            )
