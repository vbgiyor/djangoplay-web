import shutil
from pathlib import Path

import environ
from crypto import decrypt_value


def strip_quotes(value: str) -> str:
    """Remove surrounding quotes."""
    if not value:
        return value
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        return v[1:-1]
    return v

def decrypt_and_update_env():
    script_dir = Path(__file__).resolve().parent
    creds_path = script_dir.parent / "../creds.txt"
    env_path = script_dir.parent / "../.env"

    for path, name in [(creds_path, "creds.txt"), (env_path, ".env")]:
        if not path.exists():
            raise FileNotFoundError(f"{name} not found at {path}")

    env = environ.Env()
    environ.Env.read_env(str(creds_path))

    keys_to_decrypt = [
        'SITE_NAME','SITE_PROTOCOL', 'SITE_HOST', 'SITE_PORT', 'SITE_URL',
        'REDIS_HOST', 'REDIS_PORT', 'REDIS_DB',
        'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT',
        'SUPERUSER_USERNAME', 'SUPERUSER_EMAIL', 'SUPERUSER_PASSWORD',
        'DJANGO_SECRET_KEY',
        'GOOGLE_CLIENT_ID_HTTP', 'GOOGLE_CLIENT_SECRET_HTTP',
        'GOOGLE_CLIENT_ID_HTTPS', 'GOOGLE_CLIENT_SECRET_HTTPS',
        'EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD',
        'DEFAULT_FROM_EMAIL', 'SUPPORT_PHONE', 'SUPPORT_EMAIL',
        'SUPPORT_LOCATION', 'LINKEDIN_URL', 'GITHUB_URL',
    ]

    encryption_key = env.str("ENCRYPTION_KEY")
    if not encryption_key:
        raise ValueError("ENCRYPTION_KEY missing in creds.txt")
    key_bytes = encryption_key.encode("utf-8")

    # Build decrypted kv pairs
    decrypted_values = {}
    for key in keys_to_decrypt:
        ciphertext = env.str(key)
        clean = strip_quotes(ciphertext)
        decrypted_values[key] = decrypt_value(clean, key_bytes)

    # Backup .env
    backup_path = env_path.with_suffix(".env.decrypted.bak")
    shutil.copy(env_path, backup_path)
    print(f"Backed up .env → {backup_path.name}")

    new_lines = []
    encrypted_set = set(keys_to_decrypt)

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
            if key_name in encrypted_set:
                continue

            new_lines.append(line.rstrip())

    # Append plaintext block
    new_lines.append("")
    for key, value in decrypted_values.items():
        new_lines.append(f"{key}={value}")

    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines) + "\n")

    print(".env successfully restored to PLAINTEXT.")

if __name__ == "__main__":
    decrypt_and_update_env()
