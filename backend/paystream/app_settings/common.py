import logging
import os
from pathlib import Path

import environ
import tomllib
from paystream.security.crypto import decrypt_value

logger = logging.getLogger(__name__)

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False),
)

# Set the base directory and load .env file
BASE_DIR = Path(__file__).resolve().parent.parent.parent
environ.Env.read_env(os.path.join(BASE_DIR, '.env'), override=True)

# Project Root
PROJECT_ROOT = BASE_DIR.parent

# Get encryption key — try env first, then ~/.dplay/.secrets
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', '').strip()

if not ENCRYPTION_KEY:
    secrets_path = Path.home() / ".dplay" / ".secrets"
    if secrets_path.exists():
        with open(secrets_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("ENCRYPTION_KEY="):
                    ENCRYPTION_KEY = line.split("=", 1)[1].strip()
                    break

if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY not found in environment or ~/.dplay/.secrets")

key_bytes = ENCRYPTION_KEY.encode('utf-8')

def get_decrypted_value(env_var_name, default=None):
    raw = env(env_var_name, default=default)

    if raw is None:
        return default

    # detect encrypted vs plaintext
    is_ciphertext = isinstance(raw, str) and raw.startswith("gAAAAA")

    if is_ciphertext:
        return decrypt_value(raw, key_bytes)  # must decrypt or fail loudly
    else:
        return raw.strip()

DOCS_ROOT = get_decrypted_value("DOCS_ROOT", default="")
# Decrypt and expose support constants at settings import time
SUPPORT_EMAIL = get_decrypted_value("SUPPORT_EMAIL")
SUPPORT_PHONE = get_decrypted_value("SUPPORT_PHONE", "")
SUPPORT_LOCATION = get_decrypted_value("SUPPORT_LOCATION", "")
GITHUB_URL = get_decrypted_value("GITHUB_URL", "")
LINKEDIN_URL = get_decrypted_value("LINKEDIN_URL", "")
SITE_URL = get_decrypted_value("SITE_URL", "")

print("Website url from settings:", get_decrypted_value("WEBSITE_URL"))
WEBSITE_URL = get_decrypted_value("WEBSITE_URL")

SITE_ID = 1
SITE_NAME = get_decrypted_value("SITE_NAME", "")
DEFAULT_FROM_EMAIL = get_decrypted_value("DEFAULT_FROM_EMAIL")

def load_all_decrypted_values():
    """
    Decrypt all ciphertext values in os.environ IN PLACE.
    After this runs, os.environ will contain only plaintext values.
    Used by Celery bootstrap and devssl pipeline.
    """
    for key, value in list(os.environ.items()):
        if isinstance(value, str) and value.startswith("gAAAAA"):
            try:
                plaintext = decrypt_value(value, key_bytes)
                os.environ[key] = plaintext
            except Exception:
                # Best effort: Keep original ciphertext if impossible to decrypt
                logger.warning(f"Failed to decrypt env var {key}")


# Process APP_VERSION
with open(PROJECT_ROOT / "pyproject.toml", "rb") as f:
    pyproject = tomllib.load(f)

APP_VERSION = pyproject["project"]["version"]
