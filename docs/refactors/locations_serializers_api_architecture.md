# Locations App

## API Versioning & Serializer Architecture

**Status:** ✅ Frozen
**Last Updated:** 2026-01-04

---

## 1. Purpose

This document defines the **final architecture, design principles, and implementation rules** for the `locations` Django app.

The goals are to ensure:

* Long-term API stability
* Clean versioning
* DRY, maintainable code
* Schema-safe OpenAPI generation
* Enterprise-grade extensibility

This architecture is intended to be **replicated across other apps** (e.g. `industries`, `audit`, `users`) with minimal variation.

---

## 2. High-Level Design Principles

The `locations` app follows these core principles:

1. **Explicit is better than implicit**
2. **Versioning is mandatory, not optional**
3. **Read and write concerns must be separated**
4. **Views orchestrate, serializers validate, models enforce invariants**
5. **Schema generation must not depend on runtime request state**

---

## 3. API Versioning Strategy

### URL-Based Versioning

All APIs are versioned via URL paths:

```
/locations/v1/
```

Future versions (`v2`, `v3`, …) must:

* Co-exist with earlier versions
* Never break existing clients
* Live in parallel directories

---

## 4. View Layer Architecture

Views are strictly separated by **intent**, not HTTP method.

```
locations/views/v1/
├── crud/      # Write-capable ViewSets (Create / Update / Delete)
├── read/      # Read-only APIs (List / Detail / History)
├── ui/        # UI helpers (autocomplete, Select2, admin UX)
├── ops/       # Operational endpoints (bulk update, export)
└── __init__.py
```

### Responsibilities

| Layer   | Responsibility                             |
| ------- | ------------------------------------------ |
| `crud/` | Authoritative write APIs                   |
| `read/` | Safe, cacheable read APIs                  |
| `ui/`   | UI-specific helpers (non-public contracts) |
| `ops/`  | Admin / internal operational workflows     |

---

## 5. Serializer Versioning Architecture

### Directory Structure

```
locations/serializers/
├── base/                  # Version-agnostic serializers
│   ├── country.py
│   ├── region.py
│   ├── subregion.py
│   ├── city.py
│   ├── location.py
│   ├── timezone.py
│   └── __init__.py
│
├── v1/
│   ├── read/              # Response serializers
│   ├── write/             # Input serializers
│   └── __init__.py
│
└── __init__.py
```

---

## 6. Serializer Responsibilities (Strict Rules)

### 6.1 Base Serializers (`serializers/base/`)

**Purpose**

* Define canonical field mappings
* Act as inheritance anchors for versioned serializers

**Rules**

* No validation logic
* No computed fields
* No request context access
* No nested expansion
* No version-specific behavior

> Base serializers are structural only.

---

### 6.2 Read Serializers (`serializers/vX/read/`)

**Purpose**

* Define API response shape
* Preserve backward compatibility

**Allowed**

* Read-only fields (timestamps, metadata)
* Computed or derived fields
* Lightweight nesting (when justified)

**Not Required**

* Adding fields if base serializer is sufficient
  (Thin read serializers are acceptable)

---

### 6.3 Write Serializers (`serializers/vX/write/`)

**Purpose**

* Validate incoming data
* Control persistence behavior

**Rules**

* Writable fields only
* No read-only metadata
* No computed output logic
* Validation must be deterministic

---

## 7. CRUD ViewSets (Write APIs)

### Location

```
locations/views/v1/crud/
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
* destroy (soft delete)

---

## 8. Read APIs

### Structure

```
locations/views/v1/read/
├── list/
├── detail/
├── history/
└── __init__.py
```

### Characteristics

* Read-only (`GET` only)
* Safe for caching
* Explicit serializer binding
* No mutation logic

---

## 9. History APIs

### Endpoints

```
/read/history/*
```

### Serializer Policy

* Reuse **read serializers**
* No history-specific serializers unless representation diverges

**Rationale**

* History endpoints are read-only
* Consistency > specialization
* Avoid unnecessary serializer duplication

---

## 10. UI APIs

### Purpose

UI endpoints exist to support:

* Select2
* Admin UX
* Dependent dropdowns

They are **not part of the public API contract**.

```
locations/views/v1/ui/
```

---

## 11. Operational APIs (Ops)

### Purpose

* Bulk updates
* Data exports
* Admin-only workflows

### Rules

* Use **write serializers only**
* Explicitly excluded from public API documentation when needed
* Permission-guarded

```
locations/views/v1/ops/
```

---

## 12. Schema & Documentation Rules

### OpenAPI / drf-spectacular

* Every endpoint must be schema-safe
* Serializer resolution must be deterministic
* CRUD operations must declare:

  * request serializer
  * response serializer
* No runtime-dependent serializer selection

Schema generation **must succeed without a request object**.

---

## 13. DRY & Reuse Strategy

### Extracted Components

* Common filter mixins
* Base list views
* Base history views
* Base CRUD ViewSet
* Shared pagination & throttling

### Prohibited

* Duplicated queryset logic
* Repeated validation across views
* App-specific hacks inside generic layers

---

## 14. What This Architecture Enables

* Safe API evolution (`v2` without breaking `v1`)
* Predictable schema generation
* Clean separation of concerns
* Lower cognitive load per app
* Consistent refactors across the codebase

---

## 15. Final Status

* ✅ Architecture validated
* ✅ Schema generation compatible
* ✅ DRY and Django-idiomatic
* ✅ Enterprise-grade and scalable

**The `locations` app is now the canonical reference implementation.**

---
