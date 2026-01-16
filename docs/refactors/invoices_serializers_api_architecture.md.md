# Invoices App

## API Versioning & Serializer Architecture

**Status:** ✅ Frozen
**Last Updated:** 2026-01-07

---

## 1. Purpose

This document defines the **final architecture, design principles, and implementation rules** for the `invoices` Django app.

The goals are to ensure:

* Long-term API stability
* Clean and explicit versioning
* Strict separation of read vs write concerns
* Schema-safe OpenAPI generation (drf-spectacular)
* Enterprise-grade extensibility for financial workflows

The `invoices` app follows the **same canonical architecture** as `locations`, with additional rules for **financial data, history, and operational endpoints**.

---

## 2. High-Level Design Principles

The `invoices` app follows these core principles:

1. **Explicit is better than implicit**
2. **Versioning is mandatory**
3. **Read, write, ops, and UI concerns must be separated**
4. **Views orchestrate, serializers validate, models enforce invariants**
5. **Schema generation must not depend on runtime request state**
6. **Financial correctness > convenience**

---

## 3. API Versioning Strategy

### URL-Based Versioning

All invoice APIs are versioned via URL paths:

```
/api/v1/invoices/
```

Future versions (`v2`, `v3`, …) must:

* Co-exist with earlier versions
* Never break existing clients
* Live in parallel directories

No cross-version imports are allowed.

---

## 4. View Layer Architecture

Views are separated by **intent**, not HTTP verb.

```
invoices/views/v1/
├── crud/      # Write-capable ViewSets (authoritative mutations)
├── read/      # Read-only APIs (list / detail / history)
├── ui/        # UX helpers (autocomplete, lightweight search)
├── ops/       # Admin / operational workflows
└── __init__.py
```

### Responsibilities

| Layer   | Responsibility                                     |
| ------- | -------------------------------------------------- |
| `crud/` | Authoritative write APIs (state mutation)          |
| `read/` | Safe, cacheable read APIs                          |
| `ui/`   | UX helpers (non-public, non-contractual endpoints) |
| `ops/`  | Admin-only or internal operational workflows       |

---

## 5. Serializer Versioning Architecture

### Directory Structure

```
invoices/serializers/
├── base/                  # Version-agnostic canonical serializers
│   ├── invoice.py
│   ├── line_item.py
│   ├── payment.py
│   ├── payment_method.py
│   ├── status.py
│   ├── billing_schedule.py
│   ├── gst_configuration.py
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

## 6. Serializer Responsibilities (Strict Rules)

### 6.1 Base Serializers (`serializers/base/`)

**Purpose**

* Define canonical field mappings
* Serve as inheritance anchors for versioned serializers

**Rules**

* No validation logic
* No computed or derived fields
* No request context access
* No nested expansion
* No version-specific behavior

> Base serializers are **structural only**.

---

### 6.2 Read Serializers (`serializers/vX/read/`)

**Purpose**

* Define API response shape
* Preserve backward compatibility
* Support denormalized / nested representations when required

**Allowed**

* Read-only metadata fields
* Derived / computed fields (e.g. totals, formatted amounts)
* Lightweight nested serializers (read-only)

**Not Required**

* Adding fields if the base serializer already satisfies the contract
  (Thin read serializers are acceptable and encouraged)

---

### 6.3 Write Serializers (`serializers/vX/write/`)

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

## 7. CRUD ViewSets (Write APIs)

### Location

```
invoices/views/v1/crud/
```

### Mandatory ViewSet Contract

Every CRUD ViewSet **must define**:

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

## 8. Read APIs

### Structure

```
invoices/views/v1/read/
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

## 9. History APIs

### Purpose

Expose historical (audit) views of invoice-related entities.

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

**Rationale**

* History endpoints are read-only
* Consistency > specialization
* Avoid unnecessary serializer duplication

---

## 10. UI APIs

### Purpose

UI endpoints exist to support:

* Autocomplete
* Lightweight search
* Admin UX helpers

They are **not part of the public API contract**.

```
invoices/views/v1/ui/
```

### Rules

* Read-only
* Minimal logic
* No business rules
* No write operations

---

## 11. Operational APIs (Ops)

### Purpose

Operational endpoints support:

* Bulk updates (e.g. bulk status change)
* Data exports
* Admin-only derived operations

```
invoices/views/v1/ops/
```

### Rules

* Explicit permissions (admin / staff only)
* No reuse inside CRUD or read APIs
* Write serializers only
* Explicitly excluded from public API documentation when required

---

## 12. Filtering Rules (Critical)

### Default

* **Filtering is opt-in**
* Base list views must **not** enable filtering

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
* Complex cases must use explicit `FilterSet` classes

---

## 13. Schema & Documentation Rules

### drf-spectacular

* Schema generation must succeed **without a request object**
* Serializer resolution must be deterministic
* CRUD endpoints must explicitly declare:

  * request serializer
  * response serializer
* No runtime-dependent queryset or serializer switching

Warnings are acceptable; schema generation failures are not.

---

## 14. DRY & Reuse Strategy

### Shared Components

* Base list views
* Base history views
* Base CRUD ViewSet
* Shared pagination, throttling, permissions

### Prohibited

* Duplicated business logic across views
* Serializer logic inside views
* App-specific hacks inside shared base classes

---

## 15. What This Architecture Enables

* Safe API evolution (`v2` alongside `v1`)
* Predictable schema generation
* Financial correctness and auditability
* Clean separation of concerns
* Consistent refactors across all domain apps

---

## 16. Final Status

* ✅ Architecture validated
* ✅ Matches `locations` canonical design
* ✅ Schema-safe by construction
* ✅ Enterprise-grade and extensible
