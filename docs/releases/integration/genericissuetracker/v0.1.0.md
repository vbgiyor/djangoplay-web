
# 📘 GENERICISSUETRACKER INTEGRATION PLAN

Architecture: **Integration Adapter Layer (Host-Orchestrated)**
Tenant Model: **Single Tenant**
Library Policy: **No core modification, no forking**

---

# 🎯 Integration Objective

Integrate `genericissuetracker` into DjangoPlay such that:

1. Identity resolution aligns with DjangoPlay Identity layer.
2. Audit logs are recorded via existing `audit` app.
3. Permission model aligns with Employee/Role hierarchy.
4. Visibility governance enforces public vs internal control.
5. Attachments are protected via RBAC-based streaming.
6. Lifecycle transitions are policy-driven.
7. System remains fully upgrade-safe.
8. OpenAPI schema remains deterministic.

---

# 🧭 High-Level Architecture

```
GenericIssueTracker (PyPI v0.5.0)
        │
        │ (emits signals + lifecycle services)
        ▼
DjangoPlay Integration Adapter Layer
        │
        ├── Identity Resolver Adapter
        ├── Lifecycle Transition Policy
        ├── RBAC Visibility Governance
        ├── Audit Logging Integration
        ├── Attachment Security Layer
        └── Notification Hooks (future)
```

**No modification inside library core.**

All enterprise behavior lives inside:

```
paystream.integrations.issuetracker
```

---

# 🗂️ PHASED EXECUTION PLAN (UPDATED)

---

## 🟢 Phase 1 — Foundation Wiring (Infrastructure Alignment)

### Objective

Safely integrate signals, lifecycle service, and identity resolver without changing behavior.

### Scope

1. Configure:

   * `GENERIC_ISSUETRACKER_DEFAULT_PERMISSION_CLASSES`
   * `GENERIC_ISSUETRACKER_IDENTITY_RESOLVER`
   * `GENERIC_ISSUETRACKER_PAGE_SIZE`

2. Implement Integration Adapter Layer:

   ```
   paystream/integrations/issuetracker/
   ```

3. Replace default router with integrated ViewSets.

4. Capture and verify signals:

   * `issue_created`
   * `issue_commented`
   * `issue_status_changed`

5. Introduce pluggable lifecycle transition policy.

### Result

* Signals verified.
* Lifecycle transitions delegated to service layer.
* Policy-based transition enforcement.
* Zero schema mutation.
* Upgrade-safe structure established.

---

## 🟡 Phase 2 — Role-Based Visibility Governance (RBAC)

### Objective

Enforce deterministic public vs internal visibility aligned with HR role model.

### Scope

1. Introduce `IssueVisibilityService`.
2. Apply queryset-level filtering in integrated ViewSets.
3. Enforce explicit RBAC allowlist:

   ```
   ISSUE_INTERNAL_ALLOWED_ROLES = ["CEO", "DJGO", "SSO"]
   ```
4. Superuser override supported.
5. Enforce 404 masking for unauthorized detail access.
6. Restrict internal issue creation for non-privileged users.

### Security Model

| Actor                          | Public | Internal |
| ------------------------------ | ------ | -------- |
| Anonymous                      | ✔      | ✖        |
| Authenticated (non-privileged) | ✔      | ✖        |
| Privileged Roles               | ✔      | ✔        |
| Superuser                      | ✔      | ✔        |

### Result

* Deterministic RBAC enforcement.
* No serializer mutation.
* No schema change.
* Library untouched.
* Metadata leakage prevented.

---

## 🟡 Phase 3 — Attachment Governance (Security Hardening)

### Objective

Eliminate public MEDIA exposure and enforce secure file streaming.

### Problems Identified

* Attachments exposed via `/media/`
* No RBAC enforcement at file layer
* Potential internal data leakage

### Scope

1. Remove public MEDIA exposure in production.
2. Implement protected download endpoint:

   ```
   /api/v1/issuetracker/attachments/<uuid>/download/
   ```
3. Enforce:

   * RBAC visibility check
   * 404 masking
   * Access logging
4. Replace public `file` URL exposure in serializer.
5. Ensure no schema-breaking change.

### Result

* Enterprise-grade file access.
* No direct media exposure.
* Upgrade-safe.
* Access traceability introduced.

---

## 🟡 Phase 4 — Audit Logging Integration

### Objective

Integrate IssueTracker lifecycle into DjangoPlay Audit system.

### Scope

Map events to AuditLog:

| Event                | ActionType    |
| -------------------- | ------------- |
| issue_created        | CREATED       |
| issue_commented      | UPDATED       |
| issue_status_changed | STATUS_CHANGE |
| soft_delete          | DELETED       |

Tasks:

1. Resolve identity snapshot.
2. Log structured metadata payload.
3. Respect role hierarchy visibility.
4. Maintain soft-delete compatibility.

### Result

* Full audit coverage.
* Structured lifecycle tracking.
* Compliance-ready behavior.

---

## 🟡 Phase 5 — Permission Hardening

### Objective

Replace DRF default permission with enterprise-grade permission.

### Scope

Create:

```
IssueTrackerAccessPermission
```

Rules:

1. Must pass `UnifiedLoginService.validate_user()`
2. Must be active employee
3. Must not be soft-deleted
4. Must respect employment status
5. Optional write restrictions by role

Override:

```python
GENERIC_ISSUETRACKER_DEFAULT_PERMISSION_CLASSES = [
    "paystream.integrations.issuetracker.permissions.IssueTrackerAccessPermission"
]
```

### Result

* Enterprise authentication validation.
* HR-aware access enforcement.
* Soft-delete employee guard.
* Deterministic API behavior.

---

## 🟡 Phase 6 — Notification Layer (Future)

Optional phase.

* Email notification
* Slack webhook
* Workflow trigger
* Admin escalation
* Reporter status update

Fully signal-driven.
No library modification.

---

# 🧱 Architectural Guarantees

* No library forking.
* No serializer mutation.
* No monkey patching.
* Deterministic OpenAPI schema.
* Upgrade-safe.
* Explicit RBAC model.
* Service-layer domain logic preserved.

---

# 📋 Final Architecture State (Target)

After all phases:

* Lifecycle Policy Engine
* RBAC Visibility Governance
* Secure Attachment Streaming
* Full Audit Coverage
* Enterprise Permission Hardening
* Optional Notification Hooks

System becomes:

✔ Enterprise-grade
✔ Deterministic
✔ Upgrade-safe
✔ Compliant-ready
✔ Secure by design

---

# 📘 Phase 1 — Integration Adapter Layer Setup

Branch: `feature/issue-tracker-integration`

This phase is strictly **infrastructure-level wiring**.
No behavioral change yet.

---

# 🎯 Objective of Phase 1

Establish a clean integration surface between:

* `genericissuetracker`
* DjangoPlay audit + identity + mailer infrastructure

Without:

* Forking library
* Overriding library viewsets
* Introducing business logic prematurely

---

# 🧱 What We Will Create

## 📁 New Integration Module

```
paystream/
    integrations/
        __init__.py
        issuetracker/
            __init__.py
            apps.py
            signals.py
            services.py
            permissions.py
            throttling.py
```

This module becomes the **adapter boundary**.

---

# 🟢 Phase 1 Scope

## 1️⃣ Create Integration AppConfig

File:

```
paystream/integrations/issuetracker/apps.py
```

Purpose:

* Register signal listeners via `ready()`
* Ensure deterministic startup order
* Avoid circular imports

---

## 2️⃣ Signal Wiring (No Business Logic Yet)

We will listen to:

From `genericissuetracker.signals`:

* `issue_created`
* `issue_commented`
* `issue_status_changed`

And temporarily:

* Log structured payload
* Verify identity resolution works
* Verify lookup_field (`issue_number`) correctness

No audit writing yet.

---

## 3️⃣ Confirm Identity Resolver Path

Already configured:

```python
GENERIC_ISSUETRACKER_IDENTITY_RESOLVER =
    "users.services.issuetracker_identity_resolver.DjangoPlayIssueTrackerIdentityResolver"
```

Phase 1 will:

* Log resolved identity
* Ensure no `AnonymousUser` leaks
* Ensure SSO identities resolve cleanly

---

## 4️⃣ Prepare Future Throttling Hook (No Enforcement Yet)

We will:

* Define placeholder throttling class
* Not activate it yet

Future design:

```
IssueCreateThrottle
IssueUpdateThrottle
CommentCreateThrottle
```

Backed by:

```
EMAIL_FLOW_LIMITS["bug_report"]
```

We will align with your existing `allow_flow()` mechanism.

---

## 5️⃣ Prepare Permission Skeleton (No Enforcement Yet)

Define:

```
IssueTrackerAccessPermission
```

Phase 1 behavior:

* Just delegate to IsAuthenticated (or AllowAny for read)
* No hierarchy enforcement yet

Full logic comes in Phase 3.

---

# 🏗 Architecture After Phase 1

```
GenericIssueTracker
        │
        ▼
DjangoPlay Integration Signals
        │
        └── Logs only (no side effects yet)
```

System remains functionally unchanged.

---

# 🔒 Important Design Decisions Locked In

### 1️⃣ Role-based visibility enforcement

→ Implemented in Phase 4 via queryset governance

### 2️⃣ Throttling aligned with mailer flow

We will introduce new flow key:

```
"issue_submission"
```

Mapped in:

```
email_flow_limits.json
```

We will NOT reuse `bug_report` directly (clean separation).

### 3️⃣ Attachment protection strategy

We will later:

* Replace direct file URL exposure
* Serve via controlled endpoint
* Enforce permission per request

### 4️⃣ Physical file deletion strategy

When Issue soft deleted:

* Iterate active attachments
* Record:

  * original_name
  * file.path
* Delete file from storage
* Then soft-delete attachment record

All audit-logged.

---

# 📋 Phase 1 Deliverables Checklist

* [ ] Integration module created
* [ ] AppConfig registered
* [ ] Signal listeners connected
* [ ] Identity resolution verified
* [ ] Logging output confirmed
* [ ] No runtime errors
* [ ] No behavior regression

---

# 📘 PHASE 2 — ROLE-BASED VISIBILITY GOVERNANCE

Branch: `feature/issue-tracker-integration-2`

---

# 🎯 Phase 2 Objective

Enforce enterprise-grade **RBAC visibility governance** for:

* Issues
* Comments
* Attachments

Based on:

* `is_public`
* Explicit role-based allowlist
* Superuser override
* Authentication state
* Soft-delete awareness

Without:

* Modifying `genericissuetracker` core
* Breaking schema determinism
* Introducing dynamic serializer switching
* Coupling library to DjangoPlay internals
* Changing OpenAPI schema

---

# 🧠 Architectural Principle

> Visibility must be enforced at QuerySet level — not in serializer, not in template, not in frontend.

All enforcement occurs inside:

```python
get_queryset()
```

This guarantees:

* Swagger unchanged
* API schema unchanged
* Protection across list + detail endpoints
* 404 masking for unauthorized access

---

# 🟢 FINAL PHASE 2 SCOPE (ACTUAL IMPLEMENTATION)

---

## 1️⃣ Visibility Rules Definition (RBAC-Based)

We **moved away from rank-based logic** and adopted explicit RBAC allowlist.

Final rule:

| Actor                          | Can See Public | Can See Internal |
| ------------------------------ | -------------- | ---------------- |
| Anonymous                      | ✅              | ❌                |
| Authenticated (non-privileged) | ✅              | ❌                |
| Privileged Role                | ✅              | ✅                |
| Superuser (DJGO)               | ✅              | ✅                |

Configured via:

```python
ISSUE_INTERNAL_ALLOWED_ROLES = [
    "CEO",
    "DJGO",
    "SSO",
]
```

No hardcoding in logic.

Superuser override enforced:

```python
employee.is_superuser
```

Industry-aligned RBAC model.

---

## 2️⃣ QuerySet-Level Filtering Implemented

Centralized into:

```
IssueVisibilityService
```

Responsibilities:

* Resolve Employee from identity
* Apply RBAC rule
* Filter querysets consistently
* Prevent privilege leakage
* Cache employee per request

Applied in:

* `IntegratedIssueCRUDViewSet`
* `IntegratedCommentCRUDViewSet`
* `IntegratedAttachmentCRUDViewSet`

---

## 3️⃣ Detail View 404 Masking

We did NOT add explicit permission checks.

Instead, filtering happens in `get_queryset()`.

So:

```text
GET /issues/<issue_number>/
```

If internal + unauthorized → object not in queryset → 404.

✔ No existence leakage
✔ No extra permission logic
✔ Deterministic behavior

---

## 4️⃣ Comment Visibility Enforcement

Even though comments are nested, we explicitly protected:

* `/comments/`
* `/comments-read/`

By filtering:

```python
queryset.filter(issue__is_public=True)
```

Unless privileged.

✔ No indirect metadata leakage
✔ No internal comment exposure

---

## 5️⃣ Attachment Metadata Visibility

Attachment endpoints now respect:

```python
issue__is_public
```

Filtering applied via visibility service.

So:

* Unauthorized users cannot see attachment metadata
* Internal issue attachments are hidden

Note:
Public MEDIA URLs still exist (file streaming not yet protected — moved to Phase 3).

---

## 6️⃣ Internal Issue Creation Restriction (NEW)

This was not part of the original Phase 2 scope, but we added it.

Now:

> Non-privileged users cannot create internal issues.

If:

```python
issue.is_public == False
```

And user is not privileged:

```python
issue.is_public = True
```

This prevents:

* UX inconsistency
* Self-created invisible issues
* Internal issue misuse

This enforcement occurs in:

```python
IntegratedIssueCRUDViewSet.perform_create()
```

✔ Library untouched
✔ Schema unchanged
✔ Business rule enforced at integration layer

---

## 7️⃣ Superuser Override Clarified

Superuser logic explicitly supported:

```python
employee.is_superuser
```

This ensures:

* DJGO always sees internal issues
* No role-code dependency for superuser
* Alignment with Django security model

---

## 8️⃣ No Changes To

Confirmed unchanged:

* IdentityResolver contract
* Lifecycle transition policy
* Status history model
* Signals
* Serializer structure
* URL structure
* drf-spectacular schema
* Lookup via `issue_number`
* Library core logic

---

# 📦 Updated Deliverables Checklist

After Phase 2:

* [x] Anonymous cannot see internal issues
* [x] Non-privileged cannot see internal issues
* [x] Privileged roles can see internal issues
* [x] Superuser override works
* [x] 404 masking for unauthorized detail access
* [x] Comments respect issue visibility
* [x] Attachments metadata respect issue visibility
* [x] Non-privileged cannot create internal issues
* [x] Swagger unchanged
* [x] No serializer modification
* [x] No library modification
* [x] No schema change
* [x] Deterministic behavior

---

# 🔐 Security Model After Phase 2

You now have:

### Layer 1 — DRF Endpoint Permissions

### Layer 2 — Lifecycle Transition Policy (v0.5.0)

### Layer 3 — RBAC Visibility Governance (Phase 2)

### Layer 4 — Soft Delete Protection

### Layer 5 — Role-Based Internal Creation Restriction

This is production-grade access control.

---

# 🧱 What We Deferred to Phase 3

* Protected attachment file streaming
* Removal of public MEDIA access
* Signed URLs or gated download endpoint
* File access audit logging

Those are infrastructure-hardening tasks.

---

# 🏁 Phase 2 Status

Phase 2 is:

✔ Architecturally clean
✔ Security-consistent
✔ RBAC-aligned
✔ Enterprise-grade
✔ Deterministic
✔ Non-invasive to library

---


# 📘 PHASE 3 SCOPE (ATTACHMENT GOVERNANCE)

Branch: `feature/issue-tracker-integration-3`

---

# 🎯 Phase 3 Objective

Eliminate public attachment exposure and enforce secure RBAC-based file streaming.

---

# 🚨 Problem Statement

Current exposure:

```json
"file": "https://localhost:9999/media/issues/<uuid>/file.ext"
```

This allows:

* Direct media access
* Bypass of RBAC checks
* Internal data leakage
* No access logging
* No 404 masking

This is a security flaw.

---

# 🧠 Architectural Principle

> Files must be streamed via authenticated application layer — not exposed via static server.

All file access must pass through:

* Identity resolution
* RBAC visibility enforcement
* 404 masking
* Logging

---

# 🟢 Phase 3 Scope

---

## 1️⃣ Remove Public MEDIA Exposure (Production)

* Disable `/media/` static serving outside DEBUG.
* Confirm no reverse proxy exposing media.

---

## 2️⃣ Introduce Protected Download Endpoint

New route:

```
GET /api/v1/issuetracker/attachments/<uuid>/download/
```

Responsibilities:

* Resolve identity
* Apply visibility service
* 404 if unauthorized
* Stream file via `FileResponse`
* Log access

---

## 3️⃣ Replace Serializer File URL Exposure

Current:

```json
"file": "https://localhost:9999/media/..."
```

Replace with:

```json
"download_url": "https://.../attachments/<uuid>/download/"
```

Requirements:

* Do not remove original field if backward compatibility needed.
* Prefer extending read serializer in integration layer.

---

## 4️⃣ Enforce RBAC on Streaming

Reuse:

```
IssueVisibilityService
```

No duplicate logic.

---

## 5️⃣ Logging

Log:

* attachment_id
* issue_number
* identity snapshot
* timestamp

Future-ready for audit integration.

---

## 6️⃣ Optional (If Time Permits)

* Prevent physical file serving via nginx config.
* Introduce storage abstraction compatibility.

---

# 📦 Deliverables Checklist

After Phase 3:

* [ ] No public media access in production
* [ ] Attachments accessible only via API
* [ ] RBAC enforced on streaming
* [ ] Unauthorized → 404
* [ ] Access logging enabled
* [ ] Library untouched
* [ ] Schema change minimal & backward compatible

---

# 🔐 Security Level After Phase 3

You will have:

Layer 1 — DRF Endpoint Permission
Layer 2 — Lifecycle Transition Policy
Layer 3 — RBAC Visibility Governance
Layer 4 — Soft Delete Protection
Layer 5 — Secure Attachment Streaming

At this point, system becomes secure against:

* Metadata leakage
* Internal file exposure
* Direct storage bypass
* Role-based privilege escalation

---

# 📘 PHASE 4 — AUDIT LOGGING INTEGRATION (REVISED & FINAL)

Branch: `feature/issue-tracker-integration-4`

---

# 🎯 Objective

Integrate IssueTracker lifecycle events into DjangoPlay’s `audit` subsystem such that:

* All domain-significant actions are recorded
* Identity snapshot is preserved
* Audit model remains immutable and append-only
* No row-level visibility filtering is introduced
* No domain coupling is introduced
* No modification to `audit` app architecture
* Library remains untouched

---

# 🧠 Architectural Principle

> Signals orchestrate.
> Integration layer maps IssueTracker events to `AuditRecorder.record()`.
> Audit system remains pure and infrastructure-level.

We do NOT:

* Add foreign keys
* Add role-based row visibility
* Couple audit to Issue model
* Inject RBAC logic into audit layer


> The `AuditEvent` model is append-only, denormalized, immutable, and does **not** support per-row role visibility.

Therefore:

* ❌ We cannot implement row-level filtering based on `issue.is_public`
* ❌ We cannot enforce `ISSUE_INTERNAL_ALLOWED_ROLES` at audit row level
* ❌ We must not mutate the audit system design

The only architecturally sound approach is:

* ✔ Log everything
* ✔ Keep Admin access governed by `AUDIT_ADMIN_ROLES`
* ✔ Encode `is_public` inside metadata
* ✔ Keep audit system pure and domain-agnostic

---

# 🟢 Phase 4 Scope 

---

## 1️⃣ Events To Be Logged

| IssueTracker Event   | Audit `action` value                         |
| -------------------- | -------------------------------------------- |
| issue_created        | `"issue_created"`                            |
| issue_commented      | `"issue_commented"`                          |
| issue_status_changed | `"issue_status_changed"`                     |
| issue soft delete    | handled automatically via `post_soft_delete` |
| attachment uploaded  | `"attachment_uploaded"`                      |
| attachment deleted   | `"attachment_deleted"`                       |

We will NOT reuse generic words like `"created"` or `"updated"`.

We will use **explicit canonical action names**.

Reason:

* Prevent ambiguity in audit stream
* Improve filtering/search in Admin
* Maintain clarity

---

## 2️⃣ Where Logging Occurs

Inside:

```text
paystream/integrations/issuetracker/signals.py
```

We will:

* Replace logging-only handlers
* Inject calls to `AuditRecorder.record()`
* Use `AuditActor` and `AuditTarget` contracts
* Wrap calls safely (AuditRecorder already never raises)

---

## 3️⃣ Actor Mapping

We will construct:

```python
AuditActor(
    id=identity.get("id"),
    type="user",
    label=identity.get("email"),
)
```

If anonymous:

* actor = None
* `is_system_event = True`

We do NOT query Employee again.
Identity snapshot is sufficient.

---

## 4️⃣ Target Mapping

We will map:

### Issue

```python
AuditTarget(
    type="issuetracker.Issue",
    id=str(issue.id),
    label=f"Issue #{issue.issue_number}",
)
```

### Comment

```python
AuditTarget(
    type="issuetracker.Comment",
    id=str(comment.id),
    label=f"Comment on Issue #{issue.issue_number}",
)
```

### Attachment

```python
AuditTarget(
    type="issuetracker.Attachment",
    id=str(attachment.id),
    label=attachment.original_name,
)
```

---

## 5️⃣ Metadata Structure (Deterministic)

We include:

### Always

```json
{
  "issue_number": 12,
  "is_public": true
}
```

### For Status Change

```json
{
  "issue_number": 12,
  "old_status": "OPEN",
  "new_status": "IN_PROGRESS",
  "is_public": false
}
```

### For Comment

```json
{
  "issue_number": 12,
  "comment_id": "...",
  "commenter_email": "...",
  "is_public": true
}
```

### For Attachment Upload

```json
{
  "issue_number": 12,
  "attachment_id": "...",
  "original_name": "...",
  "size": 2406,
  "is_public": true
}
```

### For Attachment Delete

```json
{
  "issue_number": 12,
  "attachment_id": "...",
  "original_name": "...",
  "is_public": true
}
```

We encode `is_public` in metadata for traceability.

---

## 6️⃣ Soft Delete Handling

You already have:

```python
post_soft_delete
```

Since `Issue` model uses `soft_delete()`,
if it emits `post_soft_delete`, the audit system already logs:

```text
action="deleted"
target_type="issuetracker.Issue"
```

Therefore:

* ✔ We do NOT manually log issue deletion
* ✔ We let audit lifecycle handler capture it

We must only ensure Issue model emits signal properly (it already does in your ecosystem).

---

## 7️⃣ What We DO NOT Implement

* ❌ Row-level visibility filtering
* ❌ Special handling for internal issues
* ❌ Role-based filtering inside audit
* ❌ Domain lookups inside audit service
* ❌ Foreign keys to Issue/Comment/Attachment

---

## 8️⃣ Atomicity & Safety

* `AuditRecorder.record()` never raises
* Wrapped in try/except inside recorder
* Business flow never blocked
* No additional DB queries besides insert

---

# 🔒 Security & Governance After Phase 4

You will have:

Layer 1 — DRF Endpoint Permission
Layer 2 — Lifecycle Transition Policy
Layer 3 — RBAC Visibility Governance
Layer 4 — Secure Attachment Streaming
Layer 5 — Immutable Audit Trail

Audit remains:

* Infrastructure-level
* Immutable
* Append-only
* Role-filtered only at Admin UI level via `AUDIT_ADMIN_ROLES`

---

# 📦 Deliverables Checklist

After Phase 4:

* [ ] issue_created → audit event
* [ ] issue_commented → audit event
* [ ] issue_status_changed → audit event
* [ ] attachment_uploaded → audit event
* [ ] attachment_deleted → audit event
* [ ] issue soft_delete captured via lifecycle signal
* [ ] No schema change
* [ ] No audit model modification
* [ ] No row-level visibility
* [ ] Deterministic metadata

---

# 🏁 Architectural Integrity

This preserves:

✔ Audit subsystem purity
✔ Domain decoupling
✔ Immutable history
✔ No role-based row complexity
✔ No cross-app coupling

---

# 📘 PHASE 5 — PERMISSION HARDENING

Branch: `feature/issue-tracker-integration-5`

---

# 🎯 Objective

Replace DRF’s generic `IsAuthenticated` permission with an **enterprise-grade access control layer** aligned with:

* Unified authentication validation
* HR employment rules
* Soft-delete awareness
* Role-based write restrictions
* Deterministic API behavior

This phase ensures:

> Authentication ≠ Authorization
> Being logged in is not sufficient to access IssueTracker.

---

# 🧠 Architectural Principle

> Permission enforcement must occur at the DRF permission layer —
> not in serializer, not in ViewSet logic, not in signals.

We will implement a **single authoritative permission class**:

```
IssueTrackerAccessPermission
```

It becomes the sole entry gate for all IssueTracker endpoints.

No schema changes.
No library modification.
No serializer mutation.

---

# 🟢 Phase 5 Scope

---

## 1️⃣ Replace Default Permission

Current:

```python
GENERIC_ISSUETRACKER_DEFAULT_PERMISSION_CLASSES = [
    "rest_framework.permissions.IsAuthenticated"
]
```

Replace with:

```python
GENERIC_ISSUETRACKER_DEFAULT_PERMISSION_CLASSES = [
    "paystream.integrations.issuetracker.permissions.IssueTrackerAccessPermission"
]
```

This applies to:

* Issues
* Comments
* Attachments
* Labels
* Read + Write endpoints

---

## 2️⃣ Permission Validation Rules

### Rule 1 — Unified Authentication Validation

Must pass:

```python
UnifiedLoginService.validate_user(user)
```

This ensures:

* JWT/session integrity
* Verified user
* Non-disabled account
* No login throttling violation

If validation fails → deny.

---

### Rule 2 — Active Employee Required

Authenticated user must:

* Exist in `Employee`
* `deleted_at is null`
* Employment status is active

Soft-deleted or orphaned users are denied.

---

### Rule 3 — HR-Aware Enforcement

Employee must:

* Have valid role
* Not be suspended / inactive (if status field exists)
* Be compliant with employment policy

This ensures IssueTracker respects organizational state.

---

### Rule 4 — Optional Role-Based Write Restriction

We will optionally introduce:

```python
ISSUE_WRITE_ALLOWED_ROLES = [...]
```

If defined:

* Only these roles may:

  * POST
  * PATCH
  * DELETE
  * change-status

If not defined → allow all valid employees.

This keeps behavior configurable and deterministic.

---

### Rule 5 — Anonymous Access

If:

```python
GENERIC_ISSUETRACKER_ALLOW_ANONYMOUS_REPORTING = True
```

Allow:

* POST /issues (create only)
* No update/delete
* No status transition

Anonymous never allowed for internal issues.

---

## 3️⃣ Permission Matrix After Phase 5

| Actor                      | List | Detail | Create         | Update       | Delete       | Status Change |
| -------------------------- | ---- | ------ | -------------- | ------------ | ------------ | ------------- |
| Anonymous                  | ❌    | ❌      | ✅ (if enabled) | ❌            | ❌            | ❌             |
| Authenticated Non-Employee | ❌    | ❌      | ❌              | ❌            | ❌            | ❌             |
| Soft-Deleted Employee      | ❌    | ❌      | ❌              | ❌            | ❌            | ❌             |
| Active Employee            | ✅    | ✅      | ✅              | ✅            | ✅            | depends       |
| Role-Restricted            | ✅    | ✅      | config-based   | config-based | config-based | config-based  |
| Superuser                  | ✅    | ✅      | ✅              | ✅            | ✅            | ✅             |

---

## 4️⃣ Interaction With Previous Phases

Phase 5 integrates cleanly with:

| Layer   | Responsibility                  |
| ------- | ------------------------------- |
| Phase 2 | Visibility (public vs internal) |
| Phase 3 | Attachment streaming protection |
| Phase 4 | Audit logging                   |
| Phase 5 | Access gate hardening           |

No duplication of responsibility.

---

## 5️⃣ Security Guarantees After Phase 5

System becomes:

* Authentication validated
* Employment validated
* Role-aware
* Soft-delete aware
* Anonymous strictly controlled
* Deterministic behavior
* Fully enterprise compliant

At this point, integration is production-grade.

---

# 📦 Deliverables Checklist

After Phase 5:

* [ ] UnifiedLoginService enforced
* [ ] Soft-deleted employees blocked
* [ ] Orphaned users blocked
* [ ] Optional role-based write restriction supported
* [ ] Anonymous creation rule enforced
* [ ] Superuser override supported
* [ ] Default DRF permission removed
* [ ] No library modification
* [ ] No schema mutation
* [ ] Deterministic behavior

---

# 🧪 PHASE 5 VALIDATION MATRIX

We test:

* UnifiedLoginService enforcement
* Identity snapshot correctness
* Role-based write restriction
* Anonymous rule
* Superuser bypass
* Read/write separation
* Transition policy still works

All tests below assume:

```
/api/v1/issuetracker/
```

---

# 🧪 1️⃣ BASELINE: ACTIVE EMPLOYEE (ACTV)

**User:**

* is_active=True
* is_verified=True
* employment_status=ACTV
* role=allowed (or no restriction configured)

### Test:

```bash
GET /issues/
POST /issues/
PATCH /issues/1/
DELETE /issues/1/
POST /issues/1/change-status/
```

### Expected:

* GET → 200
* POST → 201
* PATCH → 200
* DELETE → 200
* change-status → 200

---

# 🧪 2️⃣ TERMINATED EMPLOYEE (TERM)

Update employment status to:

```
code = TERM
```

### Test:

```bash
POST /issues/
PATCH /issues/1/
DELETE /issues/1/
```

### Expected:

All → `403 Forbidden`

Reason:
`UnifiedLoginService.validate_user()` OR employment check fails.

---

# 🧪 3️⃣ SOFT-DELETED USER

Set:

```
user.deleted_at != null
```

### Test:

```bash
POST /issues/
```

### Expected:

403 Forbidden

---

# 🧪 4️⃣ UNVERIFIED USER

Set:

```
is_verified=False
```

### Test:

```bash
POST /issues/
```

### Expected:

403 Forbidden

Reason:
UnifiedLoginService rejects.

---

# 🧪 5️⃣ INACTIVE USER

Set:

```
is_active=False
```

### Test:

```bash
POST /issues/
```

### Expected:

403 Forbidden

---

# 🧪 6️⃣ ANONYMOUS USER

Log out completely.

### Test:

```bash
GET /issues/
POST /issues/
PATCH /issues/1/
DELETE /issues/1/
```

### Expected:

If:

```python
GENERIC_ISSUETRACKER_ALLOW_ANONYMOUS_REPORTING = True
```

Then:

* GET → 200 (read allowed)
* POST → 201
* PATCH → 403
* DELETE → 403

If set to False:

* POST → 403

---

# 🧪 7️⃣ ROLE WRITE RESTRICTION

Add to settings:

```python
ISSUE_WRITE_ALLOWED_ROLES = ["CEO"]
```

Use user with role:

```
FMGR
```

### Test:

```bash
POST /issues/
```

### Expected:

403 Forbidden

Use user with role:

```
CEO
```

### Expected:

201

---

# 🧪 8️⃣ SUPERUSER TEST

Set:

```
is_superuser=True
```

Even if:

* employment_status != ACTV
* is_verified=False

### Test:

```bash
POST /issues/
DELETE /issues/1/
change-status
```

### Expected:

200 / 201 (full bypass)

---

# 🧪 9️⃣ TRANSITION POLICY STILL WORKS

Ensure:

```
ISSUE_STATUS_ALLOWED_ROLES = ["CEO"]
```

Login as non-CEO employee.

### Test:

```bash
POST /issues/1/change-status/
```

### Expected:

403

Login as CEO:

200

---

# 🧪 1️⃣0️⃣ VISIBILITY STILL WORKS

Create internal issue:

```
is_public=False
```

Login as:

* Non-privileged user

### Test:

```bash
GET /issues/
GET /issues/<id>/
```

### Expected:

404

Login as privileged role:

200

---

# 🧪 1️⃣1️⃣ ATTACHMENT DOWNLOAD STILL SECURE

Internal issue attachment.

Login as non-privileged user.

```bash
GET /attachments/<id>/download/
```

Expected:
404

Login as privileged:
200

---

# 🧪 1️⃣2️⃣ AUDIT STILL LOGGING

For each successful write:

* POST
* PATCH
* DELETE
* change-status
* attachment upload
* attachment delete

Check:

```
/console/audit/auditevent/
```

Ensure entries still recorded.

---

