# Security

---

## Principles

* No credentials stored in the repository
* Secrets must remain in local `~/.dplay/` files
* `~/.dplay/.secrets` is read programmatically — never sourced by the shell
* CLI never generates secrets automatically
* CLI never writes credentials to disk
* Environment variables are encrypted at rest in `.env` via Fernet symmetric encryption

---

## Credential Flow

```
~/.dplay/.secrets  (plaintext, local only)
        │
        ▼
encrypt_env.py  (reads plaintext, writes ciphertext)
        │
        ▼
.env  (encrypted values at rest)
        │
        ▼
bootstrap_secrets.py  (decrypts into os.environ at Django startup)
        │
        ▼
Django settings  (consumes decrypted values from os.environ)
```

---

## Generating an Encryption Key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Store the output as `ENCRYPTION_KEY` in `~/.dplay/.secrets`.
Rotate by generating a new key, updating `.secrets`, and re-running `encrypt_env.py`.

---

## SSL Certificates (Local Development)

Self-signed certificates are generated under `~/.dplay/ssl/` by `djangoplay-cli`
on first run of `dplay dev ssl`. On macOS they are trusted in the System Keychain
automatically. Certificates are never committed to version control.