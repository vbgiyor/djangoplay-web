Below is the **authoritative, production-grade requirement document** for the **`mailer` app**, updated to **explicitly include**:

* The adapter clarification (Allauth / Celery–safe lazy engine access)
* The refined understanding of statelessness
* The final agreed folder structure
* The clarified positioning within the broader platform reset (without emotional language, no “Mission” wording)

This document is suitable to be:

* Checked into the repository
* Used as a reference for future contributors
* Treated as a frozen requirement for **Platform v0.2.0 — Phase 1**

---

# Email Infrastructure Refactoring — `mailer` Django App

**Platform Version:** v0.2.0
**Phase:** Phase 1 (Extraction & Stabilization)
**Status:** ✅ Implemented and Verified

---

## 1. Purpose

This document defines the **design, scope, and implementation requirements** for extracting all email-related functionality into a dedicated Django app named **`mailer`**.

The objectives are to:

* Treat email as **infrastructure**, not domain logic
* Establish **clear ownership boundaries**
* Reduce coupling between `users`, `utilities`, and presentation layers
* Preserve **100% runtime behavior**
* Prepare the platform for **future service extraction**

This change is **structural**, not functional.

---

## 2. Design Principles (Non-Negotiable)

All changes MUST adhere to the following principles.

### 2.1 Django Design Principles

* Clear ownership per app
* Explicit, one-directional dependencies
* No circular imports
* Predictable initialization order
* Testable in request-less contexts (Celery, management commands)

---

### 2.2 DRY (Do Not Repeat Yourself)

* One authoritative email engine
* One authoritative throttling implementation
* One authoritative link composition mechanism
* No duplicated email flow logic across apps

---

### 2.3 Zero Behavioral Change

The refactor MUST NOT change:

* Email content
* HTML templates
* Throttling behavior
* Token or link semantics
* API contracts
* Authentication or authorization behavior

Any deviation is considered a regression.

---

### 2.4 Service Readiness

The `mailer` app MUST be designed so that it can be extracted into a standalone service later.

This implies:

* No direct ORM dependency on domain models
* Accept structured input **contracts**, not Django models
* No reliance on request or thread-local state
* Stateless execution wherever possible

**Clarification:**
Stateless execution does **not** forbid lazy instantiation. Lazy creation of infrastructure components (e.g., `EmailEngine`) is permitted when required for framework compatibility (Allauth, Celery), provided no global or request-scoped state is retained.

---

## 3. Problem Statement (Pre-Refactor State)

Email functionality was fragmented across multiple apps.

### 3.1 `users` App

Contained:

* Email engine logic
* Inline image handling
* Email template resolution
* Unsubscribe mechanics
* Email context preparation

Issues:

* Tight coupling to identity models
* Infra logic mixed with domain logic
* Difficult to extract or test independently

---

### 3.2 `utilities` App

Contained:

* Email flow orchestration
* Throttling and rate limiting
* Verification, password reset, support flows
* Email link generation

Issues:

* Runtime infrastructure mixed with helper utilities
* Blurred ownership
* Impossible to reason about service boundaries

---

### 3.3 `frontend` App

Contained:

* HTML email templates

This placement is correct and unchanged.

---

## 4. Target Architecture

### 4.1 New App: `mailer`

`mailer` is the **single source of truth** for all email infrastructure.

It **owns**:

* Email sending engine
* Flow orchestration (verification, reset, support, notifications)
* Throttling and rate limiting
* Email-specific link composition
* Template resolution logic (not HTML)

It **does not own**:

* User identity
* Token creation
* Business decision logic
* HTML templates

---

### 4.2 Final Directory Structure

```
mailer/
├── apps.py
├── __init__.py

├── contracts/
│   └── user.py                 # EmailUser contract (no ORM)

├── engine/
│   ├── __init__.py
│   ├── base.py                 # Low-level email primitives
│   ├── engine.py               # Public EmailEngine façade
│   ├── templates.py            # Template resolution (NOT HTML)
│   ├── inline_images.py        # Inline image handling
│   ├── unsubscribe.py          # Unsubscribe mechanics
│   ├── unsubscribe_validation.py
│   └── unverified_guard.py     # Verified-email enforcement rules

├── flows/
│   ├── password_reset.py
│   ├── resend_verification.py
│   ├── support.py
│   └── member_notifications.py

├── throttling/
│   ├── flow_throttle.py
│   └── throttle.py

├── links/
│   ├── verification.py
│   ├── resend.py
│   └── unsubscribe.py

├── exceptions.py
└── tasks.py                    # Reserved for future scheduled jobs
```

---

## 5. EmailUser Contract

### 5.1 Rationale

To avoid coupling `mailer` to domain models (`Employee`, `Member`, etc.), all email operations rely on a **simple data contract**.

This ensures:

* Loose coupling
* Testability
* Framework independence
* Service extractability

---

### 5.2 Contract Definition

```python
class EmailUser:
    id: int | None
    email: str
    full_name: str | None
    is_active: bool
```

Properties:

* Constructed by the caller
* Contains only email-relevant data
* No ORM assumptions
* Serializable and service-safe

---

## 6. Ownership Boundaries

### 6.1 `mailer`

Responsible for:

* Email delivery
* Flow throttling
* Link composition
* Template resolution logic

---

### 6.2 `users`

Responsible for:

* Identity
* Authentication
* Token generation
* Workflow decisions (when to send an email)

**Important:**
Framework adapters (e.g., Allauth) may expose accessors that delegate to `mailer` infrastructure, provided no email logic is reintroduced.

Example (validated):

* Lazy `EmailEngine` access via adapter property
* Safe for Celery and request-less contexts
* No global or request state

---

### 6.3 `frontend`

Responsible for:

* HTML email templates
* Presentation and branding
* User-facing email content

---

## 7. Migration Strategy

### Phase 1 — File Relocation (Completed)

* Move all email-related files into `mailer`
* Preserve logic and behavior
* Ensure all imports resolve correctly

---

### Phase 2 — Adapter Layer (Completed)

* Existing imports in `users` and `utilities` delegate to `mailer`
* Lazy instantiation permitted where required
* No functional changes

---

### Phase 3 — Cleanup (Planned)

* Remove deprecated import paths
* Update call sites incrementally
* Introduce stricter contracts where appropriate

---

## 8. Benefits

### Immediate

* Clear separation of concerns
* Reduced complexity in `users`
* Single authoritative email subsystem
* Stable integration with Allauth and Celery

---

### Long-Term

* Ready for independent deployment
* Simplified observability and auditing
* Improved onboarding and maintainability
* Enables further platform unbundling

---

## 9. Risks and Mitigations

| Risk                         | Mitigation           |
| ---------------------------- | -------------------- |
| Circular imports             | Contract-based input |
| Behavioral regression        | Zero-change policy   |
| Over-engineering             | Minimal abstraction  |
| Framework integration issues | Adapter delegation   |

---

## 10. Current Status (Checkpoint)

At the end of Phase 1:

* ✅ Baseline pushed (`v0.1.0`)
* ✅ `mailer` app extracted and stable
* ✅ Allauth verified
* ✅ Celery verified
* ✅ No hidden regressions
* ✅ Ownership boundaries enforced

This phase is considered **complete and frozen**.

---

## Next Steps (Pending Approval)

Upon approval, proceed with:

### Phase 1.1 — Cleanup

* Remove deprecated import paths
* Consolidate transitional adapters where safe

### Phase 1.2 — Introduce EmailUser Contract

* Replace remaining implicit model usage
* Enforce contract usage across flows

### Phase 1.3 — Finalize `mailer`

* Lock `__init__.py` exports
* Freeze public API
* Mark `mailer` Phase 1 complete

---
