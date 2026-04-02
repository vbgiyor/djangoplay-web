"""
encrypt_env.py

Reads plaintext credentials from:
  ~/.dplay/config.yaml   — non-secret site and service configuration
  ~/.dplay/.secrets      — sensitive credentials and ENCRYPTION_KEY

Encrypts all tracked values and writes them into the project .env file.

Usage:
    python paystream/security/encrypt_env.py
"""

import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crypto import encrypt_value

# ------------------------------------------------------------------
# Source paths
# ------------------------------------------------------------------
DPLAY_DIR = Path.home() / ".dplay"
CONFIG_FILE = DPLAY_DIR / "config.yaml"
SECRETS_FILE = DPLAY_DIR / ".secrets"

# ------------------------------------------------------------------
# Keys written into .env as encrypted values.
# Must stay in sync with decrypt_env.py.
# ------------------------------------------------------------------
KEYS_TO_ENCRYPT = [
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
    "DOCS_ROOT", "WEBSITE_URL"
]

# Keys allowed to be blank — encrypted as empty string, not treated as error.
OPTIONAL_KEYS = {
    "REDIS_PASSWORD",
    "SITE_PORT",
    "GOOGLE_CLIENT_ID_HTTP",
    "GOOGLE_CLIENT_SECRET_HTTP",
}
# Mapping: dot-notation YAML path → env var name.
_YAML_TO_ENV = {
    "site.name":        "SITE_NAME",
    "site.protocol":    "SITE_PROTOCOL",
    "site.host":        "SITE_HOST",
    "site.port":        "SITE_PORT",
    "site.url":         "SITE_URL",
    "database.host":    "DB_HOST",
    "database.port":    "DB_PORT",
    "database.name":    "DB_NAME",
    "database.user":    "DB_USER",
    "redis.host":       "REDIS_HOST",
    "redis.port":       "REDIS_PORT",
    "redis.db":         "REDIS_DB",
    "email.host":       "EMAIL_HOST",
    "email.port":       "EMAIL_PORT",
    "email.user":       "EMAIL_HOST_USER",
    "email.from":       "DEFAULT_FROM_EMAIL",
    "support.phone":    "SUPPORT_PHONE",
    "support.email":    "SUPPORT_EMAIL",
    "support.location": "SUPPORT_LOCATION",
    "social.linkedin":  "LINKEDIN_URL",
    "social.github":    "GITHUB_URL",
    "repository.docs_root": "DOCS_ROOT",
    "site.website": "WEBSITE_URL",
}


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


def _flatten_yaml(cfg: dict) -> dict:
    """
    Walk a nested YAML dict and return a flat {ENV_KEY: value} dict
    using _YAML_TO_ENV as the lookup table.
    """
    result = {}

    def _walk(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                _walk(v, f"{path}.{k}" if path else k)
        else:
            env_key = _YAML_TO_ENV.get(path)
            if env_key:
                result[env_key] = str(node) if node is not None else ""

    _walk(cfg)
    return result


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
def encrypt_and_update_env():
    """
    Read credentials from ~/.dplay/, encrypt them, and write to .env.
    """
    # Validate source files
    for path, label in [
        (CONFIG_FILE, "~/.dplay/config.yaml"),
        (SECRETS_FILE, "~/.dplay/.secrets"),
    ]:
        if not path.exists():
            raise FileNotFoundError(f"{label} not found at {path}")

    # Load and flatten config.yaml
    with open(CONFIG_FILE, encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    flat_config = _flatten_yaml(config_data)

    # DJANGO_SECRET_KEY may live at the root level of config.yaml
    if "DJANGO_SECRET_KEY" in config_data:
        flat_config["DJANGO_SECRET_KEY"] = str(config_data["DJANGO_SECRET_KEY"])

    # Load .secrets — takes precedence over config for overlapping keys
    secrets = _load_secrets_file(SECRETS_FILE)
    all_values = {**flat_config, **secrets}

    # Resolve encryption key
    encryption_key = all_values.get("ENCRYPTION_KEY", "").strip()
    if not encryption_key:
        raise ValueError("ENCRYPTION_KEY missing in ~/.dplay/.secrets")
    key_bytes = encryption_key.encode("utf-8")

    # Guard missing required keys
    missing = [
        k for k in KEYS_TO_ENCRYPT
        if k not in OPTIONAL_KEYS and not all_values.get(k, "").strip()
    ]
    if missing:
        raise ValueError(f"Missing required keys: {', '.join(missing)}")

    # Encrypt
    encrypted_values = {}
    for key in KEYS_TO_ENCRYPT:
        raw = all_values.get(key, "")
        encrypted_values[key] = encrypt_value(_strip_quotes(raw), key_bytes)

    # Locate project .env (two levels above paystream/security/)
    script_dir = Path(__file__).resolve().parent
    env_path = script_dir.parent.parent / ".env"

    if not env_path.exists():
        env_path.touch()
        print(f" • Created new .env at {env_path}")
    else:
        backup_path = env_path.with_suffix(".env.bak")
        shutil.copy(env_path, backup_path)
        print(f" • Backed up .env → {backup_path.name}")

    # Rebuild .env: strip old encrypted keys, append fresh block
    encrypted_keys_set = set(KEYS_TO_ENCRYPT)
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
            if key_name in encrypted_keys_set:
                continue
            new_lines.append(line.rstrip())

    new_lines.append("")
    for key in KEYS_TO_ENCRYPT:
        value = encrypted_values[key].strip().strip("'\"")
        new_lines.append(f"{key}={value}")

    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines) + "\n")

    print(" • .env successfully updated with encrypted values!")


if __name__ == "__main__":
    encrypt_and_update_env()
