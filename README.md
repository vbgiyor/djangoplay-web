
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

**Important Notes**

* No app performs ad-hoc permission checks
* Permissions are cached and centrally evaluated
* Deny is the default outcome

---

## Mailer Deep Dive

The **mailer** app is a **workflow-driven email engine**, not a utility wrapper.

### Responsibilities

* Controlled transactional email delivery
* Signup, verification, reset, support, bug flows
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

### Key Design Decisions

* Emails are **events**, not side effects
* Each flow is explicit and testable
* Throttling is enforced per user and per flow
* No silent email sends

---

## Audit System Deep Dive

The **audit** app provides **system-wide observability**.

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

### Guarantees

* Actor and target are always recorded
* Audit logs are append-only
* Audit logic is decoupled from business logic

---

## Developer Onboarding Guide

### 1. Start With Boundaries

* Learn **which app owns what**
* Never bypass services

### 2. Read Services First

* Services explain the system better than views

### 3. Assume Permissions Matter

* Every endpoint is protected
* If unsure, check `policyengine`

### 4. Respect Audit Expectations

* State changes must be observable

---

## Explicit Invariants & Boundaries

### Identity Invariants

* `users.models` are not imported outside `users`
* Identity flows must use identity services

### Permission Invariants

* Authorization is centralized
* Feature flags are mandatory gates

### Service Invariants

* Views orchestrate, services decide
* Models do not contain business logic

### Audit Invariants

* No silent mutations
* No anonymous actions

---

## Configuration & Environments

* Multi-environment support (dev / staging / prod)
* Encrypted environment variables
* Redis for cache and throttling
* Celery for background tasks
* Ruff enforces architectural boundaries

---

## License

This project is licensed under the **Apache License, Version 2.0**.

```
SPDX-License-Identifier: Apache-2.0
Copyright (c) 2025
DjangoPlay - Chandrashekhar Bhosale
```

You may use, modify, and distribute this software under the terms of the Apache 2.0 License.
See `LICENSE.md` for the full license text.

---

# Commit Message (Suggested)

```
docs: add comprehensive README with architecture, identity, mailer, audit, and license details
```

---

# Release Notes (v0.2.0)

## ✨ Overview

This release introduces the **authoritative project documentation** for DjangoPlay, providing a clear, structured understanding of the system for new and existing developers.

---

## 📚 Documentation Added

* High-level system overview
* Domain-driven architecture explanation
* Identity and permission flow diagrams
* Mailer workflow deep dive
* Audit system design and guarantees
* Developer onboarding guide
* Explicit architectural invariants
* Apache 2.0 licensing information

---

## 🎯 Intended Audience

* Backend developers onboarding to DjangoPlay
* Architects reviewing system boundaries
* Contributors extending existing domains

---
