# DjangoPlay

**DjangoPlay** is a modular, enterprise-grade backend platform built with **Django and Django REST Framework**, designed for **internal organizational systems** where **identity, permissions, auditability, and correctness** are first-class concerns.

It is intentionally structured to support **long-lived systems**, regulatory requirements, and complex organizational workflows.

---

## Table of Contents

* [Overview](#overview)
* [Core Design Principles](#core-design-principles)
* [High-Level Architecture](#high-level-architecture)
* [Architecture Diagrams](#architecture-diagrams)
* [Identity & Permission Flow](#identity--permission-flow)
* [Mailer Deep Dive](#mailer-deep-dive)
* [Audit System Deep Dive](#audit-system-deep-dive)
* [Issue Tracker Integration](#issue-tracker-integration)
* [Developer Onboarding Guide](#developer-onboarding-guide)
* [Explicit Invariants & Boundaries](#explicit-invariants--boundaries)
* [Configuration & Environments](#configuration--environments)
* [License](#license)

---

## Overview

DjangoPlay provides a **comprehensive backend foundation** for:

* Employee identity and authentication
* Role- and policy-based authorization
* Organizational hierarchy (teams, departments, roles)
* Business entities and global location data
* Financial operations (invoices, payments, tax profiles)
* System-wide auditing and observability
* Controlled email workflows and throttling
* Admin UI and API documentation

It is **not** a generic CRUD system.
It is a **policy-driven, audit-aware platform**.

---

## Core Design Principles

1. **Explicit Domain Ownership**
   Each app owns its data, logic, permissions, and lifecycle.

2. **Identity as a Protected Boundary**
   Identity logic is isolated and cannot be bypassed.

3. **Service-First Architecture**
   Business logic lives in services, not views or serializers.

4. **Auditability by Default**
   Every meaningful state change is observable and attributable.

5. **Fail-Closed Security Model**
   Missing permission checks are treated as errors.

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

## Architecture Diagrams

### Domain Interaction Overview

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

## Identity & Permission Flow

### Identity Flow (Login / Signup / SSO)

```
User Action
   │
   ▼
Frontend View
   │
   ▼
users.views
   │
   ▼
users.services.identity_*
   │
   ├─ Signup / Verification
   ├─ Password Reset
   ├─ SSO Onboarding
   │
   ▼
users.models (Employee, SignupRequest)
```

**Key Characteristics**

* Tokens are short-lived and purpose-specific
* Signup, verification, and reset flows are isolated
* Identity logic is never duplicated outside `users`

---

### Permission Evaluation Flow

```
Incoming Request
   │
   ▼
Authentication
   │
   ▼
policyengine
   ├─ Role evaluation
   ├─ Action permission
   ├─ Feature flags
   │
   ▼
Allow / Deny
```

* No app performs ad-hoc permission checks
* Permissions are centrally evaluated
* Deny is the default outcome

---

## Mailer Deep Dive

The **mailer** app is a workflow-driven email engine.

### Responsibilities

* Transactional email delivery
* Signup, verification, reset, support flows
* Inline images and templating
* Unsubscribe enforcement
* Flow-level throttling

---

### Mailer Architecture

```
Service Action
   │
   ▼
Mailer Flow
   │
   ▼
Verification Guards
   │
   ▼
Template Engine
   │
   ▼
Email Adapter
   │
   ▼
SMTP / Provider
```

---

## Audit System Deep Dive

The **audit** app provides system-wide observability.

### What Is Audited

* Identity lifecycle events
* Business entity mutations
* Financial operations
* Administrative actions
* API access patterns

---

### Audit Flow

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

**Guarantees**

* Actor and target always recorded
* Append-only logs
* Decoupled from business logic

---

# Issue Tracker Integration

DjangoPlay integrates:

**genericissuetracker**

* Repository: [https://github.com/binaryfleet/issuetracker](https://github.com/binaryfleet/issuetracker)
* License: MIT
* Type: Reusable, versioned Django Issue Tracker
* Stack: Django + DRF + drf-spectacular

---

## 🌐 Subdomain Architecture

The Issue Tracker UI is mounted on a **dedicated subdomain**.

Example (local development):

```
http://issues.localhost:8000/issues/
```

Root of subdomain:

```
http://issues.localhost:8000/
```

Automatically redirects to:

```
/issues/
```

Accessing from a non-issues host returns **404**.

### Why Subdomain Isolation?

* Clear architectural boundary
* No route pollution in primary domain
* Security segmentation
* Future external/public exposure capability
* Independent scaling potential

IssueTracker UI must **not** be mounted under the main domain.

---

## Integration Architecture

```
GenericIssueTracker (Library)
        │
        ▼
DjangoPlay Integration Layer
        │
        ├── Identity Resolver
        ├── Transition Policy
        ├── DRF Permission Class
        ├── Visibility Governance
        ├── Audit Mapping
        ├── Secure Attachment Streaming
        │
        ▼
DjangoPlay UI (issues.<domain>)
```

---

## Key Integration Components

### Identity Boundary

Configured via:

```
GENERIC_ISSUETRACKER_IDENTITY_RESOLVER
```

No direct dependency on Django’s default User model.

---

### Transition Policy

Configured via:

```
GENERIC_ISSUETRACKER_TRANSITION_POLICY
```

Supports:

* Superuser override
* Owner override
* Role-based governance

---

### Visibility Governance

Implemented via `IssueVisibilityService`.

* Superuser bypass
* Role-based filtering
* Queryset-level enforcement
* 404 masking

---

### Audit Integration

Mapped domain signals:

* issue_created
* issue_updated
* issue_deleted
* issue_status_changed
* issue_commented
* attachment_uploaded
* attachment_deleted

Append-only. Failure-safe. No foreign keys.

---

### UI Layer

* Server-rendered list and detail views
* Anonymous + authenticated issue creation
* Comment + attachment support
* Status transition form
* IST timestamp formatting with naturaltime tooltip
* PRG pattern enforced

---

### Upgrade Safety

All custom logic exists in:

```
paystream.integrations.issuetracker
```

The third-party library remains untouched, guaranteeing safe upgrades.

---

## Version

Current Version: **1.0.4**

---

## Developer Onboarding Guide

1. Learn domain boundaries
2. Read services before views
3. Assume permissions matter
4. Respect audit expectations
5. IssueTracker runs under `issues.<domain>` subdomain

---

## Explicit Invariants & Boundaries

### Identity

* No identity leakage outside `users`

### Permissions

* Centralized evaluation
* Fail-closed behavior

### Services

* Views orchestrate
* Services decide

### Audit

* No silent mutations
* No anonymous state changes

---

## Configuration & Environments

* Multi-environment support
* Redis for caching
* Celery for background tasks
* Environment variable isolation
* Ruff enforces architectural boundaries

---

## License

Apache License 2.0

```
SPDX-License-Identifier: Apache-2.0
Copyright (c) 2025
DjangoPlay - Chandrashekhar Bhosale
```

---

## Intended Audience

* Backend engineers onboarding to DjangoPlay
* Architects reviewing system boundaries
* Contributors extending domains

---
