# Contributing to DjangoPlay

---

## Intended Audience

* Backend engineers onboarding to DjangoPlay
* Architects reviewing system boundaries
* Contributors extending domains

---

## Developer Onboarding Guide

1. Learn domain boundaries — each app owns its own data, logic, and permissions
2. Read services before views — business logic lives in services, not views or serializers
3. Assume permissions matter — never bypass the policy engine
4. Respect audit expectations — every meaningful state change must be observable
5. IssueTracker runs under `issues.<domain>` subdomain — do not mount it under the main domain

---

## Explicit Invariants & Boundaries

### Identity

* No identity logic outside the `users` app
* No direct access to `users.models` from other apps — use services or contracts

### Permissions

* All permission checks go through `policyengine`
* Centralized evaluation — no ad-hoc checks in views or serializers
* Fail-closed — deny is the default outcome

### Services

* Views orchestrate — they call services, they do not contain business logic
* Services decide — all domain decisions live in the service layer

### Audit

* No silent mutations — every state change must be attributable
* No anonymous state changes in authenticated flows

---

## Configuration & Environments

DjangoPlay supports multiple environments via separate settings modules:

| Module | Usage |
|---|---|
| `paystream.settings.dev` | Local development |
| `paystream.settings.staging` | Staging environment |
| `paystream.settings.prod` | Production |

Runtime dependencies:

* **Redis** — caching and Celery broker
* **Celery** — background task processing (password reset, report handling, etc.)
* **PostgreSQL** — primary database
* **Environment encryption** — credentials encrypted in `.env` via `paystream/security/encrypt_env.py`

Ruff enforces architectural import boundaries — see `pyproject.toml` for banned API rules.

---

## Local Development Setup

See the [Local Development](README.md#local-development) section in `README.md`
for the full setup guide.

---

## License

See [LICENSE](LICENSE) for details.