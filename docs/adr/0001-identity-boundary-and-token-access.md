# ADR-0001: Identity Boundary Enforcement & Signup Token Access Pattern

**Status:** Accepted
**Date:** 2026-02-04
**Decision Makers:** Backend Platform (DjangoPlay)

---

## Context

The system has a dedicated **`users` app** responsible for identity, authentication, and verification flows.
Other apps (`mailer`, `frontend`, `teamcentral`, `policyengine`, `entities`) need to *interact* with identity data but **must not couple directly to identity models**.

Historically, this led to:

* Direct imports of `users.models` outside the `users` app
* Duplicate ORM queries for signup/verification tokens
* Blurred ownership of identity vs orchestration logic

This created tight coupling and made refactors risky.

---

## Decision

We enforce a **hard identity boundary** with the following rules:

### 1. `users.models` are **private**

* Only code **inside the `users` app** may import `users.models`
* Enforced via `ruff` (`TID251`)

### 2. External access happens via **services or contracts**

* **Read-only access:** `users.contracts.*`
* **Workflow / orchestration access:** `users.services.*`

### 3. Signup / verification token access is centralized

All logic related to `SignUpRequest` lives in:

```
users.services.identity_verification_token_service.SignupTokenManagerService
```

This service exposes explicit APIs, for example:

* `create_for_user(...)`
* `validate_token(...)`
* `consume_and_activate(...)`
* `get_latest_active_request(...)` (read helper)

External apps (mailer, frontend) **must not query `SignUpRequest` directly**.

### 4. Orchestrators stay thin

Apps like `mailer`:

* Orchestrate flows (send emails, trigger tasks)
* Do not contain business rules
* Do not query identity tables

---

## Consequences

### Positive

* Clear ownership of identity logic
* No accidental ORM coupling across apps
* Single source of truth for token semantics
* Safer refactors of identity models
* Architecture enforced automatically by tooling

### Trade-offs

* Slightly more upfront discipline when adding new identity-related needs
* Requires adding small service methods instead of “quick ORM access”

These trade-offs are intentional and acceptable for a long-lived system.

---

## Example (Canonical Pattern)

**❌ Disallowed (outside `users` app):**

```python
from users.models import SignUpRequest

SignUpRequest.objects.filter(user=user).first()
```

**✅ Allowed:**

```python
from users.services.identity_verification_token_service import SignupTokenManagerService

SignupTokenManagerService.get_latest_active_request(user=user)
```

---

## Enforcement

* Automated via `ruff` (`TID251`)
* Code reviews must reject new boundary violations
* New identity access must be added via services/contracts

---

## Summary

This ADR establishes `users` as a **strict identity boundary** and formalizes the **service-based access pattern** for signup and verification tokens.
The result is a cleaner, safer, and more maintainable architecture aligned with enterprise Django best practices.

---
