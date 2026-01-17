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
# CONFIGURABLE LOGGING OPTIONS
# ============================================================================

# APPS for which automatic log files SHOULD BE generated
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

# APPS to EXCLUDE from file logging
EXCLUDE_LOG_APPS = [
    "django.db.backends"
]

# Log level defaults for all apps (can be overridden via ENV)
DEFAULT_APP_LOG_LEVEL = os.getenv("APP_LOG_LEVEL", "DEBUG")
DEFAULT_DJANGO_LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO")


# ============================================================================
# CUSTOM FORMATTER (Sumo Logic / Kafka compatible)
# ============================================================================
class CustomFormatter(jsonlogger.JsonFormatter):
    def format(self, record):
        # Timestamp (IST)
        timestamp_utc = datetime.datetime.fromtimestamp(record.created, tz=pytz.utc)
        timestamp_ist = timestamp_utc.astimezone(pytz.timezone("Asia/Kolkata"))
        formatted_timestamp = timestamp_ist.strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]

        prefix = f"IST {record.levelname} {formatted_timestamp}"

        try:
            message = record.getMessage()
        except Exception:
            message = record.msg

        record_text = (
            f'<LogRecord: {record.name}, {record.lineno}, "{message}">'
        )

        if record.exc_info:
            exc_text = self.formatException(record.exc_info).replace("\n", " | ")
            record_text = f"{record_text} [{exc_text}]"

        return f"{prefix} {record_text}"

# ============================================================================
# DYNAMIC LOG FILE MAP
# ============================================================================
LOG_FILES = {}

for app in AUTO_LOG_APPS:
    if app not in EXCLUDE_LOG_APPS:
        LOG_FILES[app] = LOG_DIR / f"{app}.log"
        LOG_FILES[app].touch(exist_ok=True)


# ============================================================================
# MAIN LOGGING CONFIGURATION (DRY)
# ============================================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "console_verbose": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S %Z",
        },
        "custom": {
            "()": CustomFormatter,
        },
    },

    "handlers": {
        "console": {
            "level": DEFAULT_DJANGO_LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "console_verbose",
        },
    },

    "loggers": {},
}


# ============================================================================
# FILE HANDLERS (auto-generated)
# ============================================================================
for app_name, logfile in LOG_FILES.items():
    handler_name = f"{app_name}_file"

    LOGGING["handlers"][handler_name] = {
        "level": DEFAULT_APP_LOG_LEVEL,
        "class": "logging.handlers.RotatingFileHandler",
        "filename": logfile,
        "maxBytes": 5 * 1024 * 1024,  # 5 MB
        "backupCount": 5,
        "formatter": "custom",
    }


# ============================================================================
# LOGGER DEFINITIONS (auto-generated)
# ============================================================================
for app_name in AUTO_LOG_APPS:
    if app_name in EXCLUDE_LOG_APPS:
        continue

    handler_name = f"{app_name}_file"

    # Django core logs use INFO; other apps use DEBUG (env configurable)
    level = DEFAULT_DJANGO_LOG_LEVEL if app_name.startswith("django") else DEFAULT_APP_LOG_LEVEL

    LOGGING["loggers"][app_name] = {
        "handlers": ["console", handler_name],
        "level": level,
        "propagate": True,
    }


# ============================================================================
# SPECIAL LOGGER: ROOT LOGGER
# ============================================================================
LOGGING["loggers"][""] = {
    "handlers": ["console"],
    "level": DEFAULT_DJANGO_LOG_LEVEL,
    "propagate": False,
}


# ============================================================================
# OPTIONAL: CELERY-SAFE QUEUE HANDLER
# ============================================================================
try:
    import queue

    LOGGING["handlers"]["async"] = {
        "level": DEFAULT_APP_LOG_LEVEL,
        "class": "logging.handlers.QueueHandler",
        "queue": queue.Queue(-1),
        "formatter": "custom",
    }

    # Attach async handler to all loggers
    for logger_name in LOGGING["loggers"]:
        LOGGING["loggers"][logger_name]["handlers"].append("async")

except ImportError:
    pass
