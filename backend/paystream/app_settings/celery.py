from .common import get_decrypted_value

# ---------------------------------------------------------------------
# REDIS CONFIG (decrypted)
# ---------------------------------------------------------------------
REDIS_HOST = get_decrypted_value("REDIS_HOST", default="localhost")
REDIS_PORT = get_decrypted_value("REDIS_PORT", default="6379")
REDIS_DB   = get_decrypted_value("REDIS_DB", default="0")
REDIS_SSL  = get_decrypted_value("REDIS_SSL", default="False").lower() == "true"

# Construct Redis URL
if REDIS_SSL:
    CELERY_BROKER_URL = f"rediss://:{''}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

CELERY_RESULT_BACKEND = CELERY_BROKER_URL

# ---------------------------------------------------------------------
# CORE WORKER SETTINGS
# ---------------------------------------------------------------------
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# ---------------------------------------------------------------------
# WORKER CONCURRENCY: Auto-adjust between macOS & Linux
# ---------------------------------------------------------------------
import platform

if platform.system() == "Darwin":
    CELERY_WORKER_POOL = "solo"
else:
    CELERY_WORKER_POOL = "prefork"

# ---------------------------------------------------------------------
# BEAT CONFIG
# ---------------------------------------------------------------------
CELERY_BEAT_SCHEDULE = {}


# ---------------------------------------------------------------------
# AUTO EXPORT FOR settings.py
# ---------------------------------------------------------------------
def configure_celery_settings(globals_dict):
    """
    Injects Celery settings into Django's settings namespace.
    """
    for key, value in globals().items():
        if key.startswith("CELERY_"):
            globals_dict[key] = value
