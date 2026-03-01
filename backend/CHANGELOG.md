# Changelog

All notable changes to the DjangoPlay web application will be documented here.

This project follows Semantic Versioning.

---

## [1.0.3] - 2026-02-28

**Tag:** `v1.0.3-issuetracker-ui-3`

### 🚀 Issue Tracker UI – Phase UI-3 (Write Operations)

### Added

* Comment submission from Issue Detail page (anonymous + authenticated)
* Policy-driven status transition form in issue header
* `IssueMutationService` for UI write orchestration
* PRG (Post-Redirect-Get) pattern for UI mutations
* Identity resolution via integration identity resolver
* Delegation to lifecycle engine for status changes
* Signal-driven audit consistency for comments and transitions

### Changed

* Status transitions fully delegated to lifecycle engine
* IssueDetailView reduced to thin orchestration layer
* No manual status mutation from UI

### Security

* Anonymous users blocked from commenting on internal issues
* Lifecycle transition policy enforced centrally
* 404 masking preserved for unauthorized access
* No business logic inside templates
* No manual signal emission from UI layer

---

## [1.0.2] - 2026-02-26

**Tag:** `v1.0.2-issuetracker-ui-2`

### 📘 Issue Tracker UI – Phase UI-2 (Detail View, Read-Only)

### Added

* Server-rendered Issue Detail page (`/issues/<issue_number>/`)
* Read-only comment thread rendering
* Secure attachment download integration
* Visibility-governed single-issue retrieval
* Prefetch optimization for comments and attachments
* Back-navigation with filter preservation
* 404 masking for unauthorized access

### Changed

* Issue list links updated to use human-friendly `issue_number`
* Query service extended for single-object retrieval

### Security

* No direct MEDIA URL exposure
* Soft-deleted issues return 404
* Strict reuse of domain visibility service
* No role checks implemented in UI layer
* No lifecycle mutation logic introduced

---

## [1.0.1] - 2026-02-24

**Tag:** `v1.0.1-issuetracker-ui-1`

### 📘 Issue Tracker UI – Phase UI-1 (Read-Only List)

### Added

* `issues_ui` integration module scaffold
* Subdomain-aware routing (`issues.<domain>`)
* Server-rendered Issue List page
* Enum-driven status filtering
* Config-driven pagination
* Deterministic ordering (`-created_at`)
* GitHub-style issue list layout
* Status and priority badge rendering
* Lock indicator for internal issues
* `IssueQueryService` abstraction layer
* Strict visibility reuse via domain visibility service

### Changed

* Introduced thin presentation boundary for Issue Tracker integration
* Explicit avoidance of API-layer HTTP calls
* Business logic removed from presentation layer

### Security

* Views never call unrestricted `.all()`
* Visibility filtering centralized
* No lifecycle or permission duplication
* No direct file URL exposure
* No business logic inside templates

---

## [1.0.0] - 2026-02-20

**Tag:** `v1.0.0-issuetracker-foundation`

### 🎉 Issue Tracker Integration Foundation

### Added

* Integration boundary for Issue Tracker domain
* Subdomain strategy (`issues.localhost`)
* Strict DRY architectural enforcement
* Thin adapter service layer
* Integration-based routing
* Enterprise-aligned layered architecture

### Security

* Domain logic treated as immutable
* No shadow models created
* No duplicate permission systems
* Lifecycle and RBAC fully delegated to domain layer

---
