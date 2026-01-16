import shutil
from pathlib import Path

import environ
from crypto import encrypt_value


def strip_quotes(value: str) -> str:
    """
    Remove surrounding single or double quotes from a string.
    Safe to call multiple times. Returns clean string.
    """
    if not value:
        return value
    stripped = value.strip()
    if len(stripped) >= 2:
        if (stripped[0] == stripped[-1]) and stripped[0] in ("'", '"'):
            return stripped[1:-1]
    return stripped


def encrypt_and_update_env():
    # Resolve paths
    script_dir = Path(__file__).resolve().parent
    creds_path = script_dir.parent / "../creds.txt"
    env_path = script_dir.parent / "../.env"

    # Validate files exist
    for path, name in [(creds_path, "creds.txt"), (env_path, ".env")]:
        if not path.exists():
            raise FileNotFoundError(f"{name} not found at {path}")

    # Read credentials using django-environ
    env = environ.Env()
    environ.Env.read_env(str(creds_path))

    # All keys you want encrypted (you intentionally keep all — respected)
    keys_to_encrypt = [
        'SITE_NAME','SITE_PROTOCOL', 'SITE_HOST', 'SITE_PORT', 'SITE_URL', 'REDIS_HOST', 'REDIS_PORT', 'REDIS_DB',
        'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT',
        'SUPERUSER_USERNAME', 'SUPERUSER_EMAIL', 'SUPERUSER_PASSWORD',
        'DJANGO_SECRET_KEY',
        'GOOGLE_CLIENT_ID_HTTP', 'GOOGLE_CLIENT_SECRET_HTTP',
        'GOOGLE_CLIENT_ID_HTTPS', 'GOOGLE_CLIENT_SECRET_HTTPS',
        'EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD', 'DEFAULT_FROM_EMAIL',
        'SUPPORT_PHONE', 'SUPPORT_EMAIL', 'SUPPORT_LOCATION', 'LINKEDIN_URL', 'GITHUB_URL'
    ]

    # Check for missing keys
    missing = [k for k in keys_to_encrypt if env.str(k, default=None) is None]
    if missing:
        raise ValueError(f"Missing required keys in creds.txt: {', '.join(missing)}")

    # Get encryption key
    encryption_key = env.str('ENCRYPTION_KEY')
    if not encryption_key:
        raise ValueError("ENCRYPTION_KEY is required in creds.txt")
    key_bytes = encryption_key.encode('utf-8')

    # Encrypt all values — with quotes stripped before encryption
    encrypted_values = {}
    for key in keys_to_encrypt:
        raw_value = env.str(key)                    # e.g. "+91-774-400-7724" or 'Pune, MH'
        clean_value = strip_quotes(raw_value)       # → +91-774-400-7724  (no quotes)
        encrypted_values[key] = encrypt_value(clean_value, key_bytes)

    # Backup current .env
    backup_path = env_path.with_suffix('.env.bak')
    shutil.copy(env_path, backup_path)
    print(f"Backed up .env → {backup_path.name}")

    # Rebuild .env — remove old versions of encrypted keys
    new_lines = []
    encrypted_keys_set = set(keys_to_encrypt)

    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()

            # Preserve blank lines and comments
            if not stripped or stripped.startswith('#'):
                new_lines.append(line.rstrip())
                continue

            # Skip malformed lines
            if '=' not in line:
                print(f"Warning: Skipping malformed line (no '='): {stripped}")
                new_lines.append(line.rstrip())
                continue

            key_name = line.split('=', 1)[0].strip()
            if key_name in encrypted_keys_set:
                continue  # We'll add fresh encrypted version below

            new_lines.append(line.rstrip())

    # Append clean encrypted block
    new_lines.append("")
    # new_lines.append("# === ENCRYPTED CREDENTIALS (DO NOT EDIT MANUALLY) ===")
    for key in keys_to_encrypt:
        encrypted = encrypted_values[key]

        # CRITICAL FIX: Force the encrypted value to be a plain string with NO quotes at all
        if isinstance(encrypted, str):
            encrypted = encrypted.strip()
            # Remove any surrounding single or double quotes that might have sneaked in
            encrypted = encrypted.strip("'").strip('"')

        # Write the line WITHOUT any quotes around the value
        new_lines.append(f"{key}={encrypted}")

    # Write back to .env
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(new_lines) + "\n")

    print(".env successfully updated with encrypted values!")
    # print("Never commit unencrypted secrets!")


if __name__ == "__main__":
    encrypt_and_update_env()
