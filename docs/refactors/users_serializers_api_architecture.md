# Users App

## API Versioning & Serializer Architecture

**Status:** ✅ Frozen
**Last Updated:** 2026-01-09

---

## 1. Purpose

This document defines the **final architecture, design principles, and implementation rules** for the `users` Django app.

The goals are to ensure:

* Long-term API stability
* Explicit and safe versioning
* Clear separation of authentication, read, write, ops, and UI concerns
* Schema-safe OpenAPI generation (drf-spectacular)
* Enterprise-grade extensibility for identity, access, and workforce domains

The `users` app follows the **same canonical architecture** as `locations` and `invoices`, with additional constraints for **authentication, security, and identity data**.

---

## 2. High-Level Design Principles

The `users` app follows these core principles:

1. **Explicit is better than implicit**
2. **Versioning is mandatory**
3. **Authentication is isolated from domain CRUD**
4. **Read, write, ops, auth, and UI concerns must be separated**
5. **Views orchestrate, serializers validate, models enforce invariants**
6. **Schema generation must not depend on runtime request state**
7. **Security correctness > convenience**

---

## 3. API Versioning Strategy

### URL-Based Versioning

All user-related APIs are versioned via URL paths:

```
/users/
/api/v1/auth/
/users/v1/
```

Key rules:

* `users/` is the canonical entrypoint for versioned APIs
* Authentication endpoints live under `/api/v1/auth/`
* Future versions (`v2`, `v3`, …) must:

  * Co-exist with earlier versions
  * Never break existing clients
  * Live in parallel directories
* No cross-version imports are allowed

---

## 4. View Layer Architecture

Views are separated by **intent**, not HTTP verb.

```
users/views/v1/
├── auth/      # Authentication & token-related APIs
├── crud/      # Write-capable APIs (authoritative mutations)
├── read/      # Read-only APIs (list / detail / history)
├── ui/        # UX helpers (autocomplete, lightweight search)
├── ops/       # Admin / operational workflows
└── __init__.py
```

### Responsibilities

| Layer   | Responsibility                                     |
| ------- | -------------------------------------------------- |
| `auth/` | Authentication, JWT, CSRF, audit logging           |
| `crud/` | Authoritative write APIs (state mutation)          |
| `read/` | Safe, cacheable read APIs                          |
| `ui/`   | UX helpers (non-public, non-contractual endpoints) |
| `ops/`  | Admin-only or internal operational workflows       |

---

## 5. Authentication Architecture

### Location

```
users/views/v1/auth/
```

### Scope

Authentication is **explicitly isolated** from domain CRUD and read APIs.

Includes:

* JWT token issuance & refresh
* CSRF token endpoints
* Authentication audit logging
* Token verification helpers

### Rules

* Authentication views **must not** depend on:

  * user CRUD serializers
  * domain viewsets
* Authentication APIs:

  * May use `AllowAny`
  * Are excluded from public schema where appropriate
* No authentication logic is allowed in:

  * CRUD views
  * Read views
  * UI views

---

## 6. Serializer Versioning Architecture

### Directory Structure

```
users/serializers/
├── base/                  # Version-agnostic canonical serializers
│   ├── user.py
│   ├── employee.py
│   ├── member.py
│   ├── address.py
│   ├── role.py
│   ├── team.py
│   ├── file_upload.py
│   ├── password_reset_request.py
│   └── __init__.py
│
├── v1/
│   ├── read/              # Response serializers
│   ├── write/             # Input / validation serializers
│   └── __init__.py
│
└── __init__.py
```

---

## 7. Serializer Responsibilities (Strict Rules)

### 7.1 Base Serializers (`serializers/base/`)

**Purpose**

* Define canonical field mappings
* Serve as inheritance anchors for versioned serializers

**Rules**

* No validation logic
* No computed or derived fields
* No request context access
* No nested expansion
* No version-specific behavior
* Fields must exactly match model columns

> Base serializers are **structural only**.

---

### 7.2 Read Serializers (`serializers/vX/read/`)

**Purpose**

* Define API response shape
* Preserve backward compatibility
* Support denormalized or nested representations when required

**Allowed**

* Read-only metadata fields
* Derived or computed fields
* Lightweight nested serializers (read-only)

**Rules**

* Must not introduce non-existent model fields
* Must not include write-only or validation-only fields
* Thin read serializers are acceptable and encouraged

---

### 7.3 Write Serializers (`serializers/vX/write/`)

**Purpose**

* Validate incoming data
* Enforce write-time invariants
* Control persistence behavior

**Rules**

* Writable fields only
* No read-only metadata
* No computed output logic
* Validation must be deterministic
* No request-context–dependent behavior

---

## 8. CRUD Views (Write APIs)

### Location

```
users/views/v1/crud/
```

### Mandatory Contract

Every CRUD view **must define explicitly**:

```python
queryset
serializer_class
```

If a ViewSet supports both read & write:

```python
read_serializer_class
write_serializer_class
```

Serializer resolution **must never depend on request context**.

### Allowed Actions

* list
* retrieve
* create
* update
* partial_update
* destroy (soft delete only)

Hard deletes are forbidden.

---

## 9. Read APIs

### Structure

```
users/views/v1/read/
├── list/
├── detail/
├── history/
└── __init__.py
```

### Characteristics

* `GET` only
* Side-effect free
* Safe for caching
* Explicit serializer binding
* No mutation logic
* No business rules

---

## 10. History APIs

### Purpose

Expose historical (audit) views of user-related entities.

### Endpoints

```
/read/history/*
```

### Rules

* Must inherit from `BaseHistoryListAPIView`
* Must define:

```python
queryset
history_queryset
serializer_class
```

* Must be schema-safe (no runtime assumptions)

### Serializer Policy

* Reuse **read serializers**
* No history-specific serializers unless representation diverges materially

---

## 11. UI APIs

### Purpose

UI endpoints exist to support:

* Autocomplete
* Lightweight search
* Admin UX helpers

They are **not part of the public API contract**.

```
users/views/v1/ui/
```

### Rules

* Read-only
* Minimal logic
* No business rules
* No write operations
* May be excluded from public schema

---

## 12. Operational APIs (Ops)

### Purpose

Operational endpoints support:

* Admin-only workflows
* Bulk actions
* Internal corrective operations

```
users/views/v1/ops/
```

### Rules

* Explicit permissions (admin / staff only)
* No reuse inside CRUD or read APIs
* Write serializers only
* Explicitly excluded from public API documentation when required

---

## 13. Filtering Rules (Critical)

### Default

* **Filtering is opt-in**
* Base list views **must not** enable filtering

### Filtered Views

Only views inheriting from:

```python
BaseFilteredListAPIView
```

may declare:

```python
filterset_fields
```

### Strict Rules

* Every field in `filterset_fields` **must exist on the queryset model**
* No implicit filter generation
* No serializer-only or computed fields
* Complex cases require explicit `FilterSet` classes

---

## 14. Schema & Documentation Rules

### drf-spectacular

* Schema generation must succeed **without a request object**
* Serializer resolution must be deterministic
* Filtering must not auto-generate invalid FilterSets
* Authentication, ops, and UI endpoints may be excluded explicitly

Warnings are acceptable.
Schema generation failures are not.

---

## 15. DRY & Reuse Strategy

### Shared Components

* Base list views
* Base filtered list views
* Base history views
* Shared pagination, throttling, permissions

### Prohibited

* Serializer logic inside views
* Runtime serializer switching
* Implicit field exposure
* App-specific hacks inside shared base classes

---

## 16. What This Architecture Enables

* Safe identity API evolution (`v2` alongside `v1`)
* Predictable schema generation
* Secure authentication isolation
* Clean separation of concerns
* Consistent refactors across all domain apps
* Reduced regression surface during future auth changes (2FA, SSO, mobile)

---

## 17. Final Status

* ✅ Architecture validated
* ✅ Matches `locations` and `invoices` canonical design
* ✅ Schema-safe by construction
* ✅ Authentication correctly isolated
* ✅ Enterprise-grade and extensible

