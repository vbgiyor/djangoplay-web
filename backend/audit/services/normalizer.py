
from audit.contracts.actor import AuditActor
from audit.contracts.target import AuditTarget


def normalize_actor(actor: AuditActor | None) -> dict[str, str | None]:
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


def normalize_target(target: AuditTarget | None) -> dict[str, str | None]:
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
