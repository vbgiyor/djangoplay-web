# DjangoPlay

**DjangoPlay** is a modular, enterprise-grade backend platform built with **Django and Django REST Framework**, designed for **internal organizational systems** where **identity, permissions, auditability, and correctness** are first-class concerns.

It is intentionally structured to support **long-lived systems**, regulatory requirements, and complex organizational workflows.

---

## Core Design Principles

* **Explicit Domain Ownership** — each app owns its data, logic, permissions, and lifecycle
* **Identity as a Protected Boundary** — identity logic is isolated and cannot be bypassed
* **Service-First Architecture** — business logic lives in services, not views or serializers
* **Auditability by Default** — every meaningful state change is observable and attributable
* **Fail-Closed Security** — missing permission checks are treated as errors

---

## Architecture

```
Client (UI / API)
   │
   ▼
Frontend (Templates / JS)
   │
   ▼
Views / ViewSets
   │
   ▼
Service Layer
   │
   ▼
Domain Models
   │
   ▼
Infrastructure
(Audit, Policy, Mailer, Cache, Signals)
```

Cross-cutting concerns are enforced **outside** domain logic.

For detailed diagrams and domain interaction maps see [docs/system/architecture.md](docs/system/architecture.md).

---

## Local Development

DjangoPlay uses **[djangoplay-cli](https://gitlab.com/djangoplay/djangoplay-cli)**
to manage the local development environment. Once the prerequisites below are
complete, the entire startup sequence — environment encryption, Redis, static
files, SSL certificates, Celery, and server — runs in a single command.

---

### System Requirements

| Dependency | Minimum Version | Notes |
|---|---|---|
| Python | 3.10+ | Use pyenv for version management |
| PostgreSQL | 14+ | Must be running locally |
| Redis | 6+ | Must be running locally |
| openssl | any | Required for SSL certificate generation |

macOS (Homebrew):

```bash
brew install postgresql redis openssl pyenv
brew services start postgresql
brew services start redis
```

Ubuntu / Debian:

```bash
sudo apt install python3.11 postgresql redis-server openssl
sudo systemctl start postgresql redis
```

---

### 1. Clone the repository

```bash
git clone https://gitlab.com/djangoplay/djangoplay-web.git
cd djangoplay-web
```

---

### 2. Create a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

---

### 3. Install dependencies

```bash
pip install -e ".[dev]"
```

---

### 4. Create the PostgreSQL database

Run the following in `psql`:

```sql
CREATE USER your_db_user WITH PASSWORD 'your_db_password';
CREATE DATABASE your_db_name OWNER your_db_user;
GRANT ALL PRIVILEGES ON DATABASE your_db_name TO your_db_user;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

> A `Makefile` to automate database setup is planned for a future release.

---

### 5. Generate an encryption key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output — you will use it as `ENCRYPTION_KEY` in the next step.

---

### 6. Create `~/.dplay/.secrets`

This file holds sensitive credentials. It is read programmatically by the CLI
and the application. Never source it in your shell profile and never commit it.

```
ENCRYPTION_KEY={{your_encryption_key}}
DJANGO_SECRET_KEY={{your_django_secret_key}}

DB_PASSWORD={{your_db_password}}
DATABASE_URL=postgresql://{{your_db_user}}:{{your_db_password}}@127.0.0.1:5432/{{your_db_name}}

SUPERUSER_USERNAME={{your_value}}
SUPERUSER_EMAIL={{your_value}}
SUPERUSER_PASSWORD={{your_value}}

REDIS_PASSWORD=

GOOGLE_CLIENT_ID_HTTPS={{your_value}}
GOOGLE_CLIENT_SECRET_HTTPS={{your_value}}
GOOGLE_CLIENT_ID_HTTP={{your_value}}
GOOGLE_CLIENT_SECRET_HTTP={{your_value}}

EMAIL_HOST_PASSWORD={{your_value}}
```

`REDIS_PASSWORD` can be left blank if Redis runs without authentication locally.
Google OAuth credentials are required for SSO login — leave blank if not testing SSO flows.

---

### 7. Create `~/.dplay/config.yaml`

```yaml
site:
  name: DjangoPlay
  protocol: https
  host: localhost
  port: 9999
  url: https://localhost:9999

repository:
  root: ~/path/to/djangoplay-web/

database:
  host: 127.0.0.1
  port: 5432
  name: {{your_db_name}}
  user: {{your_db_user}}

redis:
  host: 127.0.0.1
  port: 6379
  db: 1

email:
  mode: {{your_value}}
  host: {{your_value}}
  port: {{your_value}}
  user: {{your_value}}
  from: {{your_value}}

support:
  phone: {{your_value}}
  email: {{your_value}}
  location: {{your_value}}

social:
  linkedin: {{your_value}}
  github: {{your_value}}

django:
  settings_module: paystream.settings.dev
```

---

### 8. Run database migrations

```bash
cd backend
python manage.py migrate
```

---

### 9. Create the superuser

```bash
python manage.py create_superuser
```

Credentials are read automatically from `~/.dplay/.secrets`.
The superuser is created with a verified email address and the `DJGO` role.
If the superuser already exists the command exits safely without error.

---

### 10. Install djangoplay-cli

```bash
pip install djangoplay-cli
```

---

### 11. Start the development server

HTTPS (recommended):

```bash
dplay dev ssl
```

HTTP:

```bash
dplay dev http
```

Running `dplay dev` without a subcommand defaults to HTTP.

On first run with `dplay dev ssl`, self-signed SSL certificates are generated
under `~/.dplay/ssl/` and trusted in the macOS System Keychain automatically.
Subsequent runs reuse the existing certificates.

---

### Other useful commands

```bash
dplay system doctor   # check environment health
dplay system reset    # stop Celery, flush Redis
ruff check .          # lint
pytest                # run tests
```

---

# System Documentation

Technical reference for the DjangoPlay platform.

| Document | Description |
|---|---|
| [Architecture](docs/system/architecture.md) | Domain diagrams, layer responsibilities, environment overview |
| [Identity & Permissions](docs/system/identity-and-permissions.md) | Identity flow, permission evaluation, SSO |
| [Mailer](docs/system/mailer.md) | Email workflow engine and delivery architecture |
| [Audit System](docs/system/audit-system.md) | Observability, audit flow, and guarantees |
| [Issue Tracker](docs/system/issue-tracker.md) | IssueTracker integration and subdomain architecture |
| [Security](docs/system/security.md) | Credential flow, encryption, and SSL certificates |

---

For contributor guidelines and architectural invariants see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

See [LICENSE](LICENSE) for details.