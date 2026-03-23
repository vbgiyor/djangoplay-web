# Audit System

The **audit** app provides system-wide observability.

---

## What Is Audited

* Identity lifecycle events
* Business entity mutations
* Financial operations
* Administrative actions
* API access patterns

---

## Audit Flow

```
Action Occurs
   │
   ▼
Service / Signal
   │
   ▼
Audit Normalizer
   │
   ▼
Audit Recorder
   │
   ▼
AuditEvent Model
```

---

## Guarantees

* Actor and target always recorded
* Append-only logs — no mutation of past events
* Decoupled from business logic — audit never blocks a transaction