# Architecture

---

## High-Level Architecture

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

---

## Domain Interaction Overview

```
+------------------+        +------------------+
|      users       |        |   teamcentral    |
|------------------|        |------------------|
| Identity         |<------>| Org Structure    |
| Auth / Tokens    |        | Roles / Teams    |
+------------------+        +------------------+
          |
          v
+------------------+
|  policyengine    |
|------------------|
| Permissions      |
| Roles            |
| Feature Flags    |
+------------------+

+------------------+        +------------------+
|   entities       |<------>|    locations     |
+------------------+        +------------------+

+------------------+        +------------------+
|    invoices      |<------>|     fincore      |
+------------------+        +------------------+

+------------------+
|      audit       |
|------------------|
| System-wide logs |
+------------------+
```

---

## Architecture Layers

| Layer | Responsibility |
|---|---|
| CLI Commands | user-facing commands via djangoplay-cli |
| Views / ViewSets | thin orchestration — no business logic |
| Service Layer | all domain decisions and mutations |
| Domain Models | data ownership and lifecycle per app |
| Infrastructure | audit, policy, mailer, cache, signals |

---

## Multi-Environment Support

| Settings Module | Usage |
|---|---|
| `paystream.settings.dev` | Local development |
| `paystream.settings.staging` | Staging environment |
| `paystream.settings.prod` | Production |