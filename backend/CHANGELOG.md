# Changelog

All notable changes to the DjangoPlay web application will be documented here.

This project follows Semantic Versioning starting from **v1.0.0 (First Production Release)**.

---

## [1.0.0] - 2026-04-02

**Tag:** `v1.0.0-first-production-release`

# 🎉 First Production Release

This release marks the first production-ready version of DjangoPlay.
It stabilizes the platform architecture, admin console UX, layout system,
error handling, authentication flows, and environment configuration model.

This version represents the transition from internal development and
integration phases to a stable production-ready platform.

---

### Added

#### Platform UI & Layout System

* Unified header, footer, and page layout across admin, console, login, Redoc, and site pages
* Footer system with logo, version, links, and bug report button
* Bug report modal integration across console and documentation pages
* Consistent page wrapper and spacing system
* Unified card grid layout for app pages
* Theme toggle and space theme improvements

#### Error Handling System

* Centralized error handling for:

  * 401 Unauthorized
  * 403 Permission Denied
  * 404 Not Found
  * 500 Server Error
* Custom styled error pages with background images and themed CSS
* Django Admin permission handling integrated with custom error pages
* CSRF failures routed to custom error page
* Admin permission redirects converted to custom 403 page via AdminSite override

#### Authentication & Login

* Refactored login and API login pages to use unified layout
* Improved Django messages rendering and positioning
* Session expiry and login required handling improvements
* Logout redirect handling improvements

#### Documentation & API UI

* Redoc API documentation UI integrated with platform header/footer
* Bug report button added to Redoc interface
* Improved API login flow integration

---

### Changed

#### Admin & Console UI Refactor

* Refactored admin templates:

  * changelist_add.html
  * changelist_edit.html
  * custom_changelist.html
  * single_app.html
* Unified layout and spacing across all admin pages
* Improved header and footer alignment
* Fixed Django messages hidden under header
* Improved responsive layout behavior

#### Styling & CSS Refactor

* Refactored common.css and layout styles
* Updated support.css, openapi.css, reportbug.css
* Improved footer alignment and header spacing
* Fixed layout overlap issues
* Improved theme styling and toggle behavior

#### Error Templates Refactor

* Removed legacy error templates
* Introduced styled standalone error pages
* Unified error page styling and layout behavior

---

### Removed

* Legacy error page templates
* Obsolete CSS files
* Old layout templates and duplicated structures
* Deprecated layout patterns and unused assets

---

### Overall Result

This release stabilizes the DjangoPlay platform and introduces:

* Unified UI layout system
* Centralized error handling
* Consistent admin and console interface
* Improved authentication and session handling
* Integrated documentation and bug reporting
* Clean template and CSS structure
* Production-ready admin console experience

This version is considered the **first production-ready release** of DjangoPlay.

---

## Previous Development Releases (Pre-1.0)

### Version History Note

Before the first production release (v1.0.0), several internal releases were
tagged using feature-based version names. For clarity and proper semantic
versioning, the changelog maps those tags to logical pre-production versions
(0.x series).

Starting from **v1.0.0**, DjangoPlay follows Semantic Versioning strictly.


| Logical Version | Git Tag                  | Description                            | Details |
|-----------------|--------------------------|----------------------------------------|--------|
| 0.9.4 | v1.1.0 | CLI environment security alignment | Environment encryption/decryption aligned with CLI; credentials moved to ~/.dplay config; removed django-environ; improved secrets handling; SSL and environment workflow standardized |
| 0.9.3 | v1.0.4 | Platform improvements and integrations | Helpdesk integrated with IssueTracker; unified issue timeline; attachment security improvements; RBAC visibility governance; service layer convergence |
| 0.9.2 | v1.0.3-issuetracker-ui-3 | Issue Tracker UI Phase 3 | Comment submission; status transitions; mutation service orchestration; PRG pattern for UI writes; lifecycle integration |
| 0.9.1 | v1.0.1-issuetracker-ui-2 | Issue Tracker UI Phase 2 | Issue detail view; comment thread rendering; secure attachment downloads; visibility-governed issue retrieval; prefetch optimization |
| 0.9.0 | v1.0.0-issuetracker-ui-1 | Issue Tracker UI Phase 1 | Issue list UI; status filtering; pagination; GitHub-style list layout; visibility service integration |
| 0.1.1 | v0.1.1 | Early platform improvements | Service layer refinements; identity and permission improvements; audit logging enhancements; infrastructure cleanup; architecture refinements |
| 0.1.0 | v0.1.0 | Platform foundation | Initial domain architecture; identity system; permission model; service-first architecture; audit system foundation |
| 0.0.1 | v0.0.0.1 | Initial project setup | Initial Django project; repository structure; base apps; configuration setup; initial environment configuration |