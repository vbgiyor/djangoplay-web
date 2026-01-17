
# Audit Infrastructure  — `audit` Django App (Logging Journal)

**Platform Version:** v0.2.0

**Phase:** Phase 2 (Audit Infrastructure Extraction & Automation)

**Status:** Frozen

**Tier:** Tier-2 Infrastructure Service

---

## 1. Purpose

This document defines the **design, scope, and implementation requirements** for the dedicated Django app named **`audit`**.

The `audit` app is responsible for **observing and recording system activity** across the platform in a **decoupled, infrastructure-grade manner**, without introducing domain coupling, behavioral changes, or transactional dependencies.

The objectives are to:

* Eliminate duplicated audit logic across 100+ models
* Centralize activity tracking in a single, authoritative subsystem
* Preserve all existing soft-delete and restore semantics
* Avoid ORM-level coupling to domain models
* Ensure audit is **never on the critical execution path**
* Prepare the platform for future **audit service extraction**

This is a **structural and infrastructural refactor**, not a functional rewrite.

---

## 2. Design Principles (Non-Negotiable)

All work in Phase 2 MUST adhere strictly to the following principles.

---

### 2.1 Infrastructure-First Design

Audit is **infrastructure**, not business logic.

Therefore, audit:

* Observes facts after they occur
* Records immutable events
* Does not own domain state
* Does not enforce validation or rules
* Does not participate in workflows or transactions

Audit is **never a source of truth** — only a recorder of truth.

---

### 2.2 Zero Domain Coupling

The `audit` app MUST NOT:

* Import domain models
* Modify domain behavior
* Enforce validation
* Participate in transactions
* Depend on domain lifecycle semantics

Audit logic must remain **fully extractable**.

Domain code may **emit facts** or lifecycle events, but audit **only observes and records**.

---

### 2.3 ORM Usage Rule (Critical)

> **Audit MAY use Django ORM for persistence
> Audit MUST NOT use Django ORM for dependency**

This rule is absolute.

#### Allowed

* Plain Django models for storage
* Primitive identifiers (`int`, `str`, `uuid`)
* JSON metadata
* Read-only admin views
* Migrations

#### Forbidden

* `ForeignKey` to any domain model
* `GenericForeignKey`
* Reverse relations
* ORM joins
* Importing domain models
* Signals mutating domain objects

This rule guarantees future service extraction without refactoring caller code.

---

### 2.4 Audit Is Never a Critical Path

> **Audit failure must never block business execution.**

Therefore:

* All signal handlers are wrapped in `try/except`
* Middleware never raises
* Recorder failures are logged and swallowed
* Missing context never prevents recording

Business logic must **always succeed independently** of audit.

---

### 2.5 Zero Behavioral Change Guarantee

Phase 2 MUST NOT change:

* `save()` behavior
* `soft_delete()` behavior
* `restore()` behavior
* Admin actions
* API responses
* Permissions
* Transactions
* Error handling semantics

Only **observation and recording** are introduced.

---

## 3. Target Architecture

### 3.1 New App: `audit`

`audit` is a **Tier-2 Infrastructure Service**, similar to `mailer`.

It **owns**:

* Audit event schema
* Audit recorder service
* Actor/target normalization contracts
* Lifecycle signal handlers
* Context enrichment middleware

It **does not own**:

* Domain models
* Identity models
* Authorization
* Business rules
* Workflow orchestration

---

### 3.2 Authoritative App Structure

The following structure is **intentional and locked**:

```
audit
├── __init__.py
├── admin.py
├── apps.py
├── constants.py
├── contracts
│   ├── __init__.py
│   ├── actor.py
│   └── target.py
├── exceptions.py
├── middleware
│   ├── __init__.py
│   └── api_audit.py
├── models
│   ├── __init__.py
│   └── audit_event.py
├── services
│   ├── __init__.py
│   ├── normalizer.py
│   └── recorder.py
├── signals
│   ├── __init__.py
│   ├── events.py
│   └── lifecycle.py
├── tests.py
└── views.py

6 directories, 20 files
```

No file exists “just in case”.

---

## 4. Audit Event Model

### 4.1 Core Principle

> **Audit records facts, not references.**

Audit events are:

* Append-only
* Immutable
* Denormalized
* Free of domain dependencies

---

### 4.2 Canonical Questions Answered

Every audit record answers **five questions only**:

| Question | Fields                                              |
| -------- | --------------------------------------------------- |
| When     | `occurred_at`                                       |
| What     | `action`                                            |
| Who      | `actor_*`                                           |
| On what  | `target_*`                                          |
| Context  | `request_id`, `client_ip`, `user_agent`, `metadata` |

Nothing more.

---

### 4.3 Canonical Schema (Locked)

#### Actor (Who)

Audit never references a user model.

| Field         | Purpose                                    |
| ------------- | ------------------------------------------ |
| `actor_id`    | Opaque identifier                          |
| `actor_type`  | `employee`, `system`, `service`, `api_key` |
| `actor_email` | Optional denormalized value                |

---

#### Action (What)

| Field    | Purpose                                           |
| -------- | ------------------------------------------------- |
| `action` | Machine-readable (`deleted`, `restored`, `login`) |

---

#### Target (On What)

| Field         | Purpose                      |
| ------------- | ---------------------------- |
| `target_type` | `<app_label>.<ModelName>`    |
| `target_id`   | Primary key (stringified)    |
| `target_repr` | Snapshot via `str(instance)` |

---

#### Context

| Field        | Purpose         |
| ------------ | --------------- |
| `request_id` | Log correlation |
| `client_ip`  | Best-effort     |
| `user_agent` | Best-effort     |
| `metadata`   | JSON payload    |

---

#### Time

| Field         | Purpose             |
| ------------- | ------------------- |
| `occurred_at` | Immutable timestamp |

---

## 5. Audit Recorder Service

### 5.1 Single Write API (Mandatory)

All audit writes MUST go through:

```python
AuditRecorder.record(
    action: str,
    actor: AuditActor | None,
    target: AuditTarget | None,
    metadata: dict | None,
    is_system_event: bool = False,
    user_agent: str | None = None,
)
```

This API is **locked**.

---

### 5.2 Recorder Guarantees

The recorder:

* Never raises
* Never blocks
* Never imports domain models
* Never assumes request context exists
* Accepts contracts, not ORM instances

Failures are logged and swallowed.

---

### 5.3 Context Handling

The recorder **reads** (but does not own) contextvars exposed by core infrastructure:

* `request_id`
* `client_ip`

If unavailable, values resolve to `None`.

This preserves async safety and service extractability.

---

## 6. Lifecycle Automation (Signals)

### 6.1 Why Signals Are Used

Signals are used **only** to:

* Observe completed lifecycle transitions
* Eliminate duplicated audit logic
* Ensure 100% coverage without developer discipline

Signals never mutate data.

---

### 6.2 Observed Transitions

| Transition        | Audit Action |
| ----------------- | ------------ |
| Active → Inactive | `deleted`    |
| Deleted → Active  | `restored`   |

Eligibility rule:

```python
hasattr(model, "deleted_at") and hasattr(model, "is_active")
```

No inheritance or markers required.

---

### 6.3 Signal Architecture

* Signals emitted from base lifecycle methods only
* Handlers live in `audit/signals/lifecycle.py`
* Registered explicitly in `audit.apps.ready()`
* Wrapped in `try/except`

---

## 7. Middleware (Context Enrichment)

### 7.1 Purpose

Middleware enriches audit events with **execution context**, not business data.

Captured context:

| Field        | Source                     |
| ------------ | -------------------------- |
| `request_id` | Existing middleware        |
| `client_ip`  | Existing middleware        |
| `user_agent` | HTTP headers               |
| `actor`      | Best-effort authentication |

---

### 7.2 Contextvars Clarification

Audit:

* Does not own thread-locals
* Does not manage contextvars
* May read contextvars exposed by core

This mirrors `mailer` behavior and remains extractable.

---

## 8. Automatic vs Manual Audit

Phase 2 introduces automation **without removing manual control**.

| Scenario               | Mechanism                       |
| ---------------------- | ------------------------------- |
| Soft delete            | Automatic (signals)             |
| Restore                | Automatic (signals)             |
| API calls              | Middleware                      |
| Login/logout           | Middleware                      |
| Domain-specific events | Manual (`AuditRecorder.record`) |

Business meaning remains explicit.

---

## 9. Service Extractability Guarantee

At any time, audit persistence can be replaced by:

* Kafka producer
* REST client
* Event stream
* Async queue

Without changing:

* Domain code
* Signal emitters
* Middleware
* Recorder API

This guarantee is **non-negotiable**.

---

## 10. Benefits

### Immediate

* Centralized audit trail
* Zero duplicated logic
* Consistent metadata
* No behavioral change

### Long-Term

* Event-driven readiness
* Compliance support
* Async pipelines
* Independent deployment

---
