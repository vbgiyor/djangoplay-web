import logging
from typing import Any

from django.conf import settings

from .throttle import check_and_increment_email_limit

logger = logging.getLogger(__name__)

DEFAULTS = {
    "per_email": {"max": 3, "window_seconds": 24 * 3600},
    "per_ip": {"max": 50, "window_seconds": 24 * 3600},
}


def _merge_limits(cfg: dict | None) -> dict[str, dict[str, int]]:
    """
    Merge flow-specific config with global defaults.
    Ensures both per_email / per_ip exist and have max + window_seconds.
    """
    if not isinstance(cfg, dict):
        return DEFAULTS.copy()

    final = {}
    for key, default in DEFAULTS.items():
        final[key] = {**default, **cfg.get(key, {})}
    return final


def _get_config(flow: str) -> dict[str, dict[str, int]]:
    """
    Load limits for a flow from:
        1) settings.EMAIL_FLOW_LIMITS[flow]
        2) settings.EMAIL_FLOW_LIMITS["default"]
        3) HARD DEFAULTS
    """
    # 1) JSON or ENV loaded config
    limits_dict = getattr(settings, "EMAIL_FLOW_LIMITS", {})

    # flow-specific
    if flow in limits_dict:
        return _merge_limits(limits_dict[flow])

    # fallback default (if defined)
    if "default" in limits_dict:
        return _merge_limits(limits_dict["default"])

    # final fallback
    return DEFAULTS.copy()



def allow_flow(
    *,
    flow: str,
    user_id: int | None = None,
    email: str | None = None,
    client_ip: str | None = None,
    prefer_user_identity: bool = True,
) -> tuple[bool, str | None, dict[str, Any]]:
    """
    Unified rate-limit handler.

    Returns:
        (allowed: bool, reason: str | None, debug_info: dict)

    Order of enforcement:
      1. per-IP  (global abuse protection)
      2. per-user or per-email (identity-based control)

    Behavior:
      - Loads config from settings.<flow_cfg_name>, or DEFAULT_EMAIL_LIMITS,
        or hard-coded fallback defaults.
      - Merges defaults automatically so missing max/window values never break.
      - Uses check_and_increment_email_limit() for atomic Redis counters.

    """
    debug = {
        "flow": flow,
        "user_id": user_id,
        "email": email,
        "client_ip": client_ip,
    }

    # Load full limits dict (already merged with defaults)
    limits = _get_config(flow)

    # ===============================================================
    # 1. PER-IP LIMIT (first priority)
    # ===============================================================
    ip_value = (client_ip or "").strip() or None
    if ip_value:
        per_ip = limits["per_ip"]
        allowed_ip = check_and_increment_email_limit(
            flow=f"{flow}_ip",
            max_total=int(per_ip["max"]),
            client_ip=ip_value,
            ttl_seconds=int(per_ip["window_seconds"]),
        )
        debug["ip_allowed"] = allowed_ip

        if not allowed_ip:
            logger.info(
                "Flow '%s' blocked due to IP limit (ip=%s)",
                flow,
                ip_value,
            )
            return False, "ip_limit", debug

    # ===============================================================
    # 2. PER-USER or PER-EMAIL LIMIT
    # ===============================================================
    per_email_cfg = limits["per_email"]

    # Prefer USER identity when available
    if prefer_user_identity and user_id:
        allowed_user = check_and_increment_email_limit(
            flow=f"{flow}_user",
            max_total=int(per_email_cfg["max"]),
            user_id=user_id,
            ttl_seconds=int(per_email_cfg["window_seconds"]),
        )
        debug["user_allowed"] = allowed_user

        if not allowed_user:
            logger.warning(
                "Flow '%s' blocked due to USER limit (user_id=%s)",
                flow,
                user_id,
            )
            return False, "user_limit", debug

    else:
        # EMAIL identity path
        email_value = (email or "").strip().lower() or None
        allowed_email = check_and_increment_email_limit(
            flow=f"{flow}_email",
            max_total=int(per_email_cfg["max"]),
            email=email_value,
            ttl_seconds=int(per_email_cfg["window_seconds"]),
        )
        debug["email_allowed"] = allowed_email

        if not allowed_email:
            logger.info(
                "Flow '%s' blocked due to EMAIL limit (%s)",
                flow,
                email_value,
            )
            return False, "email_limit", debug

    # ===============================================================
    # PASS (both checks allowed)
    # ===============================================================
    return True, None, debug
