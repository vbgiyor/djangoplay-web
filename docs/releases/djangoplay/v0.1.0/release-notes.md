# Paystream Platform – Release Notes

## Version 0.1.0
**Release Type:** Initial Baseline  
**Status:** Stable Reference Snapshot

---

## Overview

This release represents the **first complete and consolidated baseline** of the Paystream platform.

It captures the platform in a fully functional state prior to any architectural refactoring, service extraction, or modularization efforts.

All future changes will be measured against this release.

---

## Included Components

### Core Platform
- Centralized Django settings and environment configuration
- Custom middleware (request ID, client IP, logging, security)
- Custom Django Admin site and console UX
- Core lifecycle and audit field models
- Permission and policy enforcement layer

### Identity & Access
- User management (employees, members, roles, teams)
- Authentication and authorization flows
- Manual and SSO signup
- Email verification and password reset
- Support and bug reporting workflows

### Domain Services
- **Locations**: global regions, countries, regions, cities, timezones
- **Industries**: industry classification and management
- **Financial Core**:
  - Addresses
  - Contacts
  - Tax profiles
- **Entities**: business entities and mappings
- **Invoices**:
  - Billing schedules
  - Line items
  - Payments
  - Status and lifecycle management

### API & Documentation
- Versioned REST APIs
- Read / write serializer separation
- OpenAPI schema generation
- Swagger and Redoc UI
- API request logging and statistics

### Frontend Experience
- Authentication UI (login, signup, verification, reset)
- Console dashboard
- Error and access pages
- Email templates (HTML and fallback text)

### Utilities & Infrastructure
- API base views and viewsets
- Filtering, pagination, and bulk operations
- Rate limiting and throttling
- Email workflow helpers
- Validation and normalization utilities
- Background task scaffolding

---

## Architectural Notes

- This release intentionally preserves the existing monolithic structure.
- No attempt has been made to extract services or refactor ownership boundaries.
- Serializer and view architecture is considered stable and frozen at this point.
- This release is the **starting point** for planned improvements such as:
  - Email infrastructure isolation
  - Centralized audit logging
  - Dependency inversion around identity
  - Service-readiness improvements

---

## Upgrade / Migration Notes

Not applicable. This is the initial baseline release.

---

## Next Planned Work

- Infrastructure refactoring (email subsystem)
- Audit logging centralization
- Gradual reduction of cross-app coupling
- Service boundary definition
