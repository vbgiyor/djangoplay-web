import json
import logging
import os
from pathlib import Path

from .common import BASE_DIR, decrypt_value, env, key_bytes

logger = logging.getLogger(__name__)

# -------------------------
# EMAIL BACKEND SELECTION
# -------------------------
EMAIL_MODE = env("EMAIL_MODE", default="smtp")  # smtp | console | disabled

if EMAIL_MODE == "console":
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
elif EMAIL_MODE == "disabled":
    EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# -------------------------
# SMTP SETTINGS (encrypted)
# -------------------------
EMAIL_HOST = decrypt_value(env("EMAIL_HOST", default="smtp.gmail.com"), key_bytes)
EMAIL_PORT = int(decrypt_value(env("EMAIL_PORT", default="587"), key_bytes))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = decrypt_value(env("EMAIL_HOST_USER"), key_bytes)
EMAIL_HOST_PASSWORD = decrypt_value(env("EMAIL_HOST_PASSWORD"), key_bytes)

DEFAULT_FROM_EMAIL = decrypt_value(env("DEFAULT_FROM_EMAIL"), key_bytes)

# -------------------------
# BUG REPORT EMAIL SETTINGS
# -------------------------
REPORT_BUG_ENABLED = True
REPORT_BUG_ENABLED_ON_URLS = [
    "console_dashboard",
    "admin_single_app",
    "swagger-ui",
    "redoc",
    "console:index",
    "console:app_list",
    "report_bug",
]

REPORT_BUG_MAX_ATTACHMENT_SIZE_MB = 10
REPORT_BUG_ALLOWED_FILE_TYPES = [
    "image/jpeg",
    "image/png",
    "application/pdf",
    "text/plain",
    "text/log",
]

# -------------------------
# EMAIL RATE LIMITS (YOUR ORIGINAL LOGIC PRESERVED)
# -------------------------
FALLBACK_EMAIL_FLOW_LIMITS = {
    "default": {
        "per_email": {"max": 2, "window_seconds": 86400},
        "per_ip": {"max": 10, "window_seconds": 86400},
    }
}

def load_email_flow_limits():
    # (1) ENV override
    raw = os.getenv("EMAIL_FLOW_LIMITS")
    if raw:
        try:
            logger.info("Loading EMAIL_FLOW_LIMITS from environment")
            return json.loads(raw)
        except Exception as e:
            logger.error("Invalid EMAIL_FLOW_LIMITS JSON in env: %s", e)

    # (2) JSON config file
    config_path = Path(BASE_DIR) / "kb" / "config" / "email_flow_limits.json"
    if config_path.exists():
        try:
            logger.info(f"Loading email flow limits from {config_path}")
            with open(config_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Invalid email_flow_limits.json: {e}")

    # (3) Default fallback
    logger.warning("Using fallback EMAIL_FLOW_LIMITS defaults")
    return FALLBACK_EMAIL_FLOW_LIMITS

EMAIL_FLOW_LIMITS = load_email_flow_limits()
