import hashlib
import logging
from typing import Optional

from django.core.cache import cache

logger = logging.getLogger(__name__)


def _build_throttle_key(
    flow: str,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> str:
    """
    Build a stable cache key based on flow + identity:

    Priority:
      1) user_id
      2) email
      3) client_ip
      4) global (fallback)
    """
    if user_id is not None:
        ident = f"user:{user_id}"
    elif email:
        ident = f"email:{hashlib.sha256(email.lower().encode('utf-8')).hexdigest()}"
    elif client_ip:
        ident = f"client_ip:{client_ip}"
    else:
        ident = "global"

    return f"email_throttle:{flow}:{ident}"


def check_and_increment_email_limit(
    *,
    flow: str,
    max_total: int,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    client_ip: Optional[str] = None,
    ttl_seconds: Optional[int] = None,
) -> bool:
    """
    Generic email throttle.

    Returns True if we're allowed to send (and increments the counter),
    False if max_total has already been reached.

    - flow: unique key for this flow, e.g. "signup_request_ack"
    - max_total: max count allowed for this flow+identity
    - user_id / email / client_ip: who the email is about. Priority:
        user_id → email → client_ip → global
    - ttl_seconds: optional expiration for the counter; if None → no expiry
    """
    if max_total <= 0:
        # defensive: if misconfigured, just block rather than spam
        return False

    key = _build_throttle_key(flow, user_id=user_id, email=email, client_ip=client_ip)

    # Read current safely
    current = cache.get(key, 0)
    try:
        current_int = int(current)
    except (TypeError, ValueError):
        current_int = 0

    if current_int >= max_total:
        logger.info(
            "email_throttle: blocked flow=%s user_id=%s email=%s client_ip=%s "
            "(current=%s, max_total=%s)",
            flow, user_id, email, client_ip, current_int, max_total,
        )
        return False

    # Under limit → increment
    # Use cache.add(..., timeout=ttl_seconds) so TTL is set on first creation
    if cache.get(key) is not None:
        try:
            new_value = cache.incr(key)
            # If TTL provided, refresh TTL to ensure window behaviour
            if ttl_seconds is not None:
                # cache.touch exists for django-redis; no-op if backend doesn't support
                try:
                    cache.touch(key, ttl_seconds)
                except Exception:
                    # not all backends support touch; ignore gracefully
                    pass
        except ValueError:
            # Rare race: key vanished between get and incr — re-add with TTL
            if ttl_seconds is not None:
                cache.add(key, 1, timeout=ttl_seconds)
            else:
                cache.add(key, 1)
            new_value = 1
    else:
        # create with TTL if provided
        if ttl_seconds is not None:
            cache.add(key, 1, timeout=ttl_seconds)
        else:
            cache.add(key, 1)
        new_value = 1

    logger.info(
        "email_throttle: allowed flow=%s user_id=%s email=%s client_ip=%s "
        "(new_value=%s, max_total=%s)",
        flow, user_id, email, client_ip, new_value, max_total,
    )
    return True
