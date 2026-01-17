from typing import Any, Dict, Optional

from audit.contracts.actor import AuditActor
from audit.contracts.target import AuditTarget


def normalize_actor(actor: Optional[AuditActor]) -> Dict[str, Optional[str]]:
    if not actor:
        return {
            "actor_id": None,
            "actor_type": None,
            "actor_label": None,
        }

    return {
        "actor_id": str(actor.id) if actor.id is not None else None,
        "actor_type": actor.type,
        "actor_label": actor.label,
    }


def normalize_target(target: Optional[AuditTarget]) -> Dict[str, Optional[str]]:
    if not target:
        return {
            "target_type": None,
            "target_id": None,
            "target_label": None,
        }

    return {
        "target_type": target.type,
        "target_id": str(target.id) if target.id is not None else None,
        "target_label": target.label,
    }
