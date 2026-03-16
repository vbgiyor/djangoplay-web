# Changelog

All notable changes to the DjangoPlay web application will be documented here.

This project follows Semantic Versioning.

---

## [1.1.0] - 2026-03-16

**Tag:** `v1.1.0-cli-aligned-environment-security`

### Security & Developer Experience — CLI-Aligned Environment Management

This patch streamlines environment encryption and decryption to align with
the `djangoplay-cli` library. Credentials are now read exclusively from
`~/.dplay/config.yaml` and `~/.dplay/.secrets`, removing the previous
dependency on `creds.txt` and `django-environ`.


### Changed

* `paystream/security/encrypt_env.py` — reads credentials from `~/.dplay/config.yaml`
  and `~/.dplay/.secrets` instead of `creds.txt`; `django-environ` dependency removed;
  YAML flattened via internal mapping table; `.secrets` values take precedence over
  config for overlapping keys
* `paystream/security/decrypt_env.py` — reads `ENCRYPTION_KEY` exclusively from
  `~/.dplay/.secrets`; `creds.txt` and `django-environ` dependency removed
* both scripts use direct `sys.path` injection for `crypto` import to support
  standalone subprocess execution by `djangoplay-cli`
* `DJANGO_SETTINGS_MODULE` sourced from `~/.dplay/config.yaml` under `django.settings_module`

### Removed

* dependency on `creds.txt` for encryption and decryption workflows
* dependency on `django-environ` in security scripts

### Security

* `~/.dplay/.secrets` is read programmatically only — never sourced by the shell
* SSL certificates stored locally under `~/.dplay/ssl/` — never committed to version control

---

## [1.1.0] - 2026-03-06

**Tag:** `v1.1.0-helpdesk-issuetracker-convergence`

### 🚀 Helpdesk → IssueTracker Convergence

### Added

* Helpdesk → Issue adapter layer
* automatic bug and support synchronization with IssueTracker
* management command `migrate_helpdesk_to_issues`
* unified issue activity timeline in Issue Detail view
* `IssueTimelineService` for event aggregation
* timeline partial template system
* comment attachment rendering inside timeline
* bug visibility labels (`🐞 INTERNAL`, `🐞 PUBLIC`)
* automatic label bootstrap service
* role-based issue visibility governance service
* DjangoPlay identity resolver for IssueTracker integration
* issue source annotation (`bug_report` vs `issue`)

### Changed

* Helpdesk services now delegate issue creation to `IssueMutationService`
* bug and support flows internally create Issues
* issue UI now renders a unified activity timeline

### Security

* internal attachment storage paths are no longer exposed
* attachment downloads remain protected via secure endpoints
* visibility rules enforced through centralized service

---

## [1.0.4] - 2026-03-03

**Tag:** `v1.0.4-issuetracker-ui-4`

### 🚀 Issue Tracker UI – Phase UI-4 (Write + Governance Completion)

This release completes the full IssueTracker integration lifecycle.

---

### Added

* Issue creation UI (anonymous + authenticated)
* Comment submission with attachment support
* Status transition form integrated with lifecycle engine
* `IssueMutationService` for UI orchestration
* Protected attachment download endpoint
* Enterprise `IssueStateTransitionOwnerPolicy`

  * Superuser bypass
  * Owner override
  * Configurable role-based governance
* Complete domain signal → audit integration
* Timestamp partial (IST format + naturaltime tooltip)
* Proper Django messages handling in base template
* IssueTracker UI mounted under dedicated issues subdomain

---

### Changed

* Status transitions fully delegated to lifecycle engine
* Transition policy hardened for enterprise RBAC
* Identity resolution unified across UI and API
* Visibility governance applied consistently (list, detail, attachments)

---

### Security

* No direct file URL exposure
* 404 masking preserved
* RBAC enforcement at queryset level
* No business logic in templates
* No permission duplication
* Strict PRG pattern for UI writes

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
* Dedicated IssueTracker subdomain strategy (issues.<domain>)

### Security

* Domain logic treated as immutable
* No shadow models created
* No duplicate permission systems
* Lifecycle and RBAC fully delegated to domain layer

---