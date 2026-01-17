import datetime
import os
from pathlib import Path

import pytz
from pythonjsonlogger import jsonlogger

# ============================================================================
# BASE DIRECTORIES
# ============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# CONFIGURATION FLAGS
# ============================================================================
ENABLE_ASYNC_LOGGING = os.getenv("ENABLE_ASYNC_LOGGING", "false").lower() == "true"

DEFAULT_APP_LOG_LEVEL = os.getenv("APP_LOG_LEVEL", "DEBUG")
DEFAULT_DJANGO_LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO")

# ============================================================================
# APPLICATION GROUPS
# ============================================================================
AUTO_LOG_APPS = [
    "users",
    "locations",
    "industries",
    "entities",
    "invoices",
    "frontend",
    "apidocs",
    "policyengine",
    "mailer",
    "audit",
    "django",
    "django_redis",
    "data_sync",
]

EXCLUDE_LOG_APPS = [
    "django.db.backends",
]

# ============================================================================
# CUSTOM FORMATTER
# ============================================================================
class CustomFormatter(jsonlogger.JsonFormatter):
    def format(self, record):
        timestamp_utc = datetime.datetime.fromtimestamp(record.created, tz=pytz.utc)
        timestamp_ist = timestamp_utc.astimezone(pytz.timezone("Asia/Kolkata"))
        ts = timestamp_ist.strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]

        prefix = f"IST {record.levelname} {ts}"

        try:
            message = record.getMessage()
        except Exception:
            message = record.msg

        record_text = f'<LogRecord: {record.name}, {record.lineno}, "{message}">'

        if record.exc_info:
            exc_text = self.formatException(record.exc_info).replace("\n", " | ")
            record_text = f"{record_text} [{exc_text}]"

        return f"{prefix} {record_text}"

# ============================================================================
# LOG FILE MAP
# ============================================================================
LOG_FILES = {}

for app in AUTO_LOG_APPS:
    if app not in EXCLUDE_LOG_APPS:
        path = LOG_DIR / f"{app}.log"
        path.touch(exist_ok=True)
        LOG_FILES[app] = path

# ============================================================================
# BASE LOGGING STRUCTURE
# ============================================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "console": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
        "structured": {
            "()": CustomFormatter,
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": DEFAULT_DJANGO_LOG_LEVEL,
            "formatter": "console",
        },
    },

    "loggers": {},
}

# ============================================================================
# FILE HANDLERS (ALWAYS PRESENT)
# ============================================================================
for app_name, logfile in LOG_FILES.items():
    LOGGING["handlers"][f"{app_name}_file"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": logfile,
        "maxBytes": 5 * 1024 * 1024,
        "backupCount": 5,
        "level": DEFAULT_APP_LOG_LEVEL,
        "formatter": "structured",
    }

# ============================================================================
# OPTIONAL ASYNC HANDLER (DEFINED ONCE)
# ============================================================================
if ENABLE_ASYNC_LOGGING:
    import queue

    LOGGING["handlers"]["async"] = {
        "class": "logging.handlers.QueueHandler",
        "queue": queue.Queue(-1),
        "level": DEFAULT_APP_LOG_LEVEL,
        "formatter": "structured",
    }

# ============================================================================
# APPLICATION LOGGERS (SINGLE SOURCE OF TRUTH)
# ============================================================================
for app_name in AUTO_LOG_APPS:
    if app_name in EXCLUDE_LOG_APPS:
        continue

    if ENABLE_ASYNC_LOGGING:
        handlers = ["async"]
    else:
        handlers = ["console", f"{app_name}_file"]

    LOGGING["loggers"][app_name] = {
        "handlers": handlers,
        "level": (
            DEFAULT_DJANGO_LOG_LEVEL
            if app_name.startswith("django")
            else DEFAULT_APP_LOG_LEVEL
        ),
        "propagate": False,
    }

# ============================================================================
# ROOT LOGGER (CONSOLE ONLY)
# ============================================================================
LOGGING["loggers"][""] = {
    "handlers": ["console"],
    "level": DEFAULT_DJANGO_LOG_LEVEL,
    "propagate": False,
}
