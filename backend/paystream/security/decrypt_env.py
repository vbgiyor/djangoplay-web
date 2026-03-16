"""
decrypt_env.py

Reads ENCRYPTION_KEY from ~/.dplay/.secrets, decrypts all tracked
values from the project .env, and writes plaintext back into .env.

Usage:
    python paystream/security/decrypt_env.py
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crypto import decrypt_value

# ------------------------------------------------------------------
# Source paths
# ------------------------------------------------------------------
DPLAY_DIR = Path.home() / ".dplay"
SECRETS_FILE = DPLAY_DIR / ".secrets"

# ------------------------------------------------------------------
# Keys to decrypt — must stay in sync with encrypt_env.py
# ------------------------------------------------------------------
KEYS_TO_DECRYPT = [
    "SITE_NAME", "SITE_PROTOCOL", "SITE_HOST", "SITE_PORT", "SITE_URL",
    "REDIS_HOST", "REDIS_PORT", "REDIS_DB", "REDIS_PASSWORD",
    "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT",
    "SUPERUSER_USERNAME", "SUPERUSER_EMAIL", "SUPERUSER_PASSWORD",
    "DJANGO_SECRET_KEY",
    "GOOGLE_CLIENT_ID_HTTP", "GOOGLE_CLIENT_SECRET_HTTP",
    "GOOGLE_CLIENT_ID_HTTPS", "GOOGLE_CLIENT_SECRET_HTTPS",
    "EMAIL_HOST", "EMAIL_PORT", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD",
    "DEFAULT_FROM_EMAIL",
    "SUPPORT_PHONE", "SUPPORT_EMAIL", "SUPPORT_LOCATION",
    "LINKEDIN_URL", "GITHUB_URL",
]


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------
def _strip_quotes(value: str) -> str:
    """Remove surrounding single or double quotes."""
    if not value:
        return value
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        return v[1:-1]
    return v


def _load_secrets_file(path: Path) -> dict:
    """Parse a KEY=VALUE file into a plain dict."""
    values = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------
def decrypt_and_update_env():
    """
    Decrypt all tracked values in .env back to plaintext.
    """
    if not SECRETS_FILE.exists():
        raise FileNotFoundError(f"~/.dplay/.secrets not found at {SECRETS_FILE}")

    secrets = _load_secrets_file(SECRETS_FILE)

    encryption_key = secrets.get("ENCRYPTION_KEY", "").strip()
    if not encryption_key:
        raise ValueError("ENCRYPTION_KEY missing in ~/.dplay/.secrets")
    key_bytes = encryption_key.encode("utf-8")

    # Locate project .env
    script_dir = Path(__file__).resolve().parent
    env_path = script_dir.parent.parent / ".env"

    if not env_path.exists():
        raise FileNotFoundError(f".env not found at {env_path}")

    # Read current encrypted values from .env
    env_values = {}
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            env_values[key.strip()] = value.strip()

    # Decrypt
    decrypted_values = {}
    for key in KEYS_TO_DECRYPT:
        ciphertext = env_values.get(key, "")
        if not ciphertext:
            decrypted_values[key] = ""
            continue
        try:
            decrypted_values[key] = decrypt_value(_strip_quotes(ciphertext), key_bytes)
        except ValueError as exc:
            raise ValueError(f"Failed to decrypt {key}: {exc}") from exc

    # Backup
    backup_path = env_path.with_suffix(".env.decrypted.bak")
    shutil.copy(env_path, backup_path)
    print(f"Backed up .env → {backup_path.name}")

    # Rebuild .env: strip encrypted versions, append plaintext block
    decrypted_keys_set = set(KEYS_TO_DECRYPT)
    new_lines = []

    with open(env_path, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                new_lines.append(line.rstrip())
                continue
            if "=" not in line:
                new_lines.append(line.rstrip())
                continue
            key_name = line.split("=", 1)[0].strip()
            if key_name in decrypted_keys_set:
                continue
            new_lines.append(line.rstrip())

    new_lines.append("")
    for key, value in decrypted_values.items():
        new_lines.append(f"{key}={value}")

    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines) + "\n")

    print(".env successfully restored to PLAINTEXT.")


if __name__ == "__main__":
    decrypt_and_update_env()
