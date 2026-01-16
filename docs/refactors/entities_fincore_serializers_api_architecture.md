## API Versioning & Serializer Architecture
# Apps: Fincore & Entities

**Status:** ✅ Frozen
**Last Updated:** 2026-01-05

---
# Fincore App

## 1. Purpose

This document defines the **final architecture, design principles, and implementation rules** for the `fincore` Django app.

The `fincore` app provides **shared financial domain primitives** used across the platform, including:

* Addresses
* Contacts
* Tax profiles
* Entity mappings

The architecture mirrors the `locations` app and exists to ensure:

* Reuse across multiple business domains
* Strict API versioning
* Predictable schema generation
* Clean separation between read, write, and UI concerns

---

## 2. High-Level Design Principles

The `fincore` app follows the same core principles as `locations`:

1. **Versioning is mandatory**
2. **Read and write concerns must be separated**
3. **Shared primitives must remain generic**
4. **Views orchestrate, serializers validate, models enforce**
5. **Schema generation must be request-independent**

---

## 3. API Versioning Strategy

### URL-Based Versioning

All APIs are exposed under:

```
/fincore/v1/
```

Future versions must:

* Co-exist with previous versions
* Preserve backward compatibility
* Live in parallel directories

---

## 4. View Layer Architecture

```
fincore/views/v1/
├── crud/      # Write-capable ViewSets
├── read/      # Read-only APIs (list / detail / history)
├── ui/        # UI helpers (autocomplete, admin UX)
├── ops/       # Operational / admin-only workflows
└── __init__.py
```

### Responsibility Split

| Layer   | Responsibility                                |
| ------- | --------------------------------------------- |
| `crud/` | Create / Update / Delete financial primitives |
| `read/` | Safe, cacheable read APIs                     |
| `ui/`   | UX helpers (Select2, dropdowns)               |
| `ops/`  | Bulk / internal operations                    |

---

## 5. Serializer Versioning Architecture

```
fincore/serializers/
├── base/              # Canonical structural serializers
│   ├── address.py
│   ├── contact.py
│   ├── tax_profile.py
│   └── __init__.py
│
├── v1/
│   ├── read/          # Response serializers
│   ├── write/         # Input serializers
│   └── __init__.py
│
└── __init__.py
```

---

## 6. Serializer Responsibilities

### 6.1 Base Serializers

**Purpose**

* Define canonical field mappings
* Act as inheritance anchors

**Rules**

* No validation logic
* No request context
* No computed fields
* No nested expansions

---

### 6.2 Read Serializers

**Purpose**

* Define response representation
* Preserve backward compatibility

**Allowed**

* Computed / derived fields
* Read-only metadata
* Lightweight relations

---

### 6.3 Write Serializers

**Purpose**

* Validate input
* Control persistence

**Rules**

* Deterministic validation
* Writable fields only
* No response-only metadata

---

## 7. CRUD ViewSets

All write-capable ViewSets **must define**:

```python
read_serializer_class
write_serializer_class
```

Serializer selection **must not depend on request context**.

Allowed actions:

* list
* retrieve
* create
* update
* partial_update
* destroy (soft delete)

---

## 8. Read APIs

```
fincore/views/v1/read/
├── list/
├── detail/
├── history/
└── __init__.py
```

Characteristics:

* GET-only
* Cache-safe
* Explicit serializer binding
* No mutation logic

---

## 9. History APIs

* Use **read serializers**
* No history-specific serializers unless representation diverges
* Must remain read-only

---

## 10. UI APIs

UI endpoints support:

* Autocomplete
* Admin UX helpers
* Dependent dropdowns

They are **non-public contracts** and may evolve independently.

```
fincore/views/v1/ui/
```

---

## 11. Operational APIs (Ops)

Purpose:

* Bulk operations
* Internal workflows
* Admin-only utilities

Rules:

* Write serializers only
* Permission guarded
* Explicitly excluded from public schema if needed

---

## 12. Schema & Documentation Rules

* Schema generation must succeed without a request
* No runtime serializer resolution
* Explicit request/response serializers
* drf-spectacular compatibility is mandatory

---

## 13. Final Status

* ✅ Shared primitives cleanly isolated
* ✅ Schema-safe and versioned
* ✅ Approved as a core reusable domain layer

**The `fincore` app is now frozen and stable.**

---

---

# Entities App

## API Versioning & Serializer Architecture

**Status:** ✅ Frozen
**Last Updated:** 2026-01-05

---

## 1. Purpose

This document defines the **final architecture and design rules** for the `entities` Django app.

The `entities` app models **business and organizational entities** and acts as a **composition layer** over:

* `fincore` primitives (address, contact, tax profile)
* `industries`
* Access-control logic

---

## 2. Design Principles

In addition to the global principles:

1. **Entities orchestrate domain relationships**
2. **Business rules live in models and serializers**
3. **Views remain thin**
4. **Composition > duplication**

---

## 3. API Versioning Strategy

All APIs are exposed under:

```
/entities/v1/
```

Version rules mirror `locations` and `fincore`.

---

## 4. View Layer Architecture

```
entities/views/v1/
├── crud/      # Write-capable APIs
├── read/      # Read-only APIs
├── ui/        # UI helpers (autocomplete)
├── ops/       # Admin / operational workflows
└── __init__.py
```

---

## 5. Serializer Versioning Architecture

```
entities/serializers/
├── base/              # Structural serializers
│   ├── entity.py
│   └── __init__.py
│
├── v1/
│   ├── read/          # Response serializers
│   ├── write/         # Input serializers
│   └── __init__.py
│
└── __init__.py
```

---

## 6. Serializer Responsibilities

### Base Serializers

* Define canonical entity fields
* No validation logic
* No nested fincore expansions

---

### Read Serializers

* Aggregate fincore data (addresses, contacts, tax profiles)
* Include computed / derived fields
* Preserve backward compatibility

---

### Write Serializers

* Validate entity business rules
* Coordinate fincore associations
* No response-only fields

---

## 7. CRUD ViewSets

CRUD ViewSets must define:

```python
read_serializer_class
write_serializer_class
```

Rules:

* No business logic in views
* No serializer switching via request context
* All persistence flows through serializers / models

---

## 8. Read APIs

```
entities/views/v1/read/
├── list/
├── detail/
├── history/
└── __init__.py
```

Characteristics:

* Read-only
* Cacheable
* Explicit serializer usage

---

## 9. History APIs

* Reuse read serializers
* No write logic
* Consistent representation across time

---

## 10. UI APIs

UI endpoints:

* Support autocomplete and UX flows
* Are non-public contracts
* Must remain schema-safe

```
entities/views/v1/ui/
```

---

## 11. Operational APIs (Ops)

* Admin-only workflows
* Bulk operations
* Explicit permissions
* Write serializers only

---

## 12. Schema & Documentation Rules

* drf-spectacular compatibility required
* No implicit serializer resolution
* Deterministic schema generation
* No request-dependent behavior

---

## 13. Final Status

* ✅ Clean composition over fincore
* ✅ Business rules centralized
* ✅ Safe for future versioning
