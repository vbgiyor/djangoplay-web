# 🧠 Issue Tracker UI – Architecture & Roadmap (DRY + Enterprise-Aligned)

This document defines the **architectural strategy and phased roadmap** for building the server-rendered UI layer for the `genericissuetracker` library inside DjangoPlay (Paystream).

---

# 🏗 Architectural Strategy (Strictly DRY)

We are enforcing a **clean layered architecture** with zero business-logic duplication.

```
issues_ui (Presentation Layer)
        ↓
Integration Service Layer (Thin Adapter)
        ↓
genericissuetracker (Domain Logic)
        ↓
RBAC + Audit + Signals (Already Implemented)
```

---

## 🚫 What We Will NOT Do

* ❌ No HTTP calls to `/api/v1/issuetracker/`
* ❌ No duplicated permission checks
* ❌ No reimplementation of visibility rules
* ❌ No direct MEDIA exposure
* ❌ No business logic inside templates
* ❌ No lifecycle or transition logic in UI

---

## ✅ Correct Integration Pattern

UI views must:

* Call visibility service
* Call existing permission classes
* Call existing transition services (in later phases)
* Render templates

**Conceptual pattern:**

```python
class IssueListView(LoginRequiredMixin, TemplateView):
    template_name = "issues/list.html"

    def get_queryset(self):
        return IssueVisibilityService.get_visible_issues(self.request.user)
```

This guarantees:

* Single source of truth
* Thin presentation layer
* Centralized domain logic
* Library remains untouched

---

# 📁 Architectural Placement

UI lives inside the integration boundary:

```
paystream/
    integrations/
        issuetracker/
            ui/
                urls.py
                views/
                    read/
                        issue_list.py
                services/
                    issue_query_service.py
                templates/issues/
                    list.html
                    partials/
```

We are extending the **integration layer**, not creating:

* ❌ A new domain
* ❌ A shadow Issue model
* ❌ A second permission system
* ❌ A duplicate lifecycle engine

---

# 🌐 Subdomain Strategy (Future-Proof)

## Local Development

```
https://issues.localhost:9999/issues/
```

You already configured:

```
127.0.0.1 issues.localhost
```

Your `mkcert` setup includes:

```
mkcert localhost issues.localhost 127.0.0.1 ::1
```

No new certificates required.

To activate subdomain locally:

```bash
export SITE_HOST=issues.localhost
```

---

## Production (Future)

```
https://issues.djangoplay.com/issues/
```

Example Nginx:

```nginx
server_name issues.djangoplay.com;

location / {
    proxy_pass http://django_app;
}
```

---

## Django Host Routing

If host starts with `issues.`:

```python
if request.get_host().startswith("issues."):
    include("issues_ui.urls")
```

(Will be refined using Django `Site` framework in UI-4.)

---

## Subdomain Behavior Matrix

| Host                  | Behavior                |
| --------------------- | ----------------------- |
| issues.localhost      | Issue UI routes only    |
| localhost             | Normal Paystream routes |
| issues.djangoplay.com | Issue UI routes only    |

Root on subdomain:

```
/  → redirect → /issues/
```

---

# 🗺 Implementation Roadmap (Locked Order)

## UI-1 

* `issues_ui` app scaffold
* Subdomain-aware routing
* Issue List View
* Enum-driven status filtering
* Pagination (library-config driven)
* Strict visibility reuse

## UI-2

* DetailView
* Comment thread
* Secure attachment links

## UI-3

* CreateView
* Comment form
* Status transition form
* Django messages integration

## UI-4

* Production subdomain binding
* Site-based routing
*  UI polish

---

# 🔐 Security Guarantees

The UI layer:

* Never calls `.all()` directly in views
* Always goes through visibility service
* Uses existing permission classes
* Uses signed URLs for attachments
* Respects `EmploymentStatus.ACTIVE`
* Never mutates `genericissuetracker`
* Never bypasses lifecycle validation

UI is strictly presentation.

---

# 📘 Phase UI-1 — Read-Only Issue List

## 🎯 Objective

Introduce a **server-rendered UI** for the third-party library:

```
genericissuetracker
```

Mounted exclusively on the issues subdomain.

Delivered:

* Subdomain-aware routing
* GitHub-style issue list
* Enum-driven status filter
* Config-driven pagination
* Strict visibility governance
* Zero duplication of business logic

---

# 🧱 Design Principles Applied

### 1️⃣ Third-Party Boundary Respect

Imports strictly from:

```python
from genericissuetracker.models import Issue, IssueStatus, IssuePriority
```

Never from integration shadow modules.

We treat `genericissuetracker` as immutable.

---

### 2️⃣ Thin Views

Location:

```
ui/views/read/issue_list.py
```

Responsibilities:

* Parse query parameters
* Call `IssueQueryService`
* Handle pagination
* Render template

Must NOT:

* Apply business filtering
* Perform role checks
* Implement lifecycle rules

---

### 3️⃣ Service-Layer Query Abstraction

Location:

```
ui/services/issue_query_service.py
```

Responsibilities:

1. Base queryset:

```python
Issue.objects.all()
```

(Soft-delete respected automatically.)

2. Apply visibility filtering
3. Apply enum-driven status filtering
4. Apply deterministic ordering
5. Return clean queryset

Reusable for:

* UI-2 detail page
* UI-3 dashboard
* Future search features

---

# 🔎 URL Endpoints (UI-1)

| URL        | Behavior                    |
| ---------- | --------------------------- |
| `/`        | Redirect → `/issues/`       |
| `/issues/` | Issue list page (read-only) |

No other endpoints in this phase.

---

# 🔁 Status Filtering

Supported:

```
/issues/?status=ALL
/issues/?status=OPEN
/issues/?status=IN_PROGRESS
/issues/?status=RESOLVED
/issues/?status=CLOSED
```

Rules:

* Default: `ALL`
* Values derived from:

```python
IssueStatus.choices
```

* No hardcoded literals
* Invalid values → fallback to `ALL`

---

# 🔄 Query Flow (Strict DRY)

```
IssueListView
    ↓
IssueQueryService.get_issues_for_list(user, status)
    ↓
Issue.objects.all()
    ↓
VisibilityService.filter_queryset(...)
    ↓
Apply enum status filter
    ↓
order_by("-created_at")
```

Views never filter directly.

---

# 📄 Pagination

* Page size derived from:

```
GENERIC_ISSUETRACKER_PAGE_SIZE
```

* Resolved using:

```python
from genericissuetracker.services.pagination import resolve_page_size
```

* Uses Django `Paginator`
* No hardcoded page size

---

# 🎨 UI Rendering Requirements

Each issue row displays:

* Status badge (enum-driven)
* Issue number
* Title
* Priority badge
* Comment count (`issue.comments.count()`)
* Created time (naturaltime)
* Reporter email
* Lock icon if `is_public=False`

---

## Badge Mapping (UI Concern Only)

### Status → Bootstrap

| Status      | Class     |
| ----------- | --------- |
| OPEN        | success   |
| IN_PROGRESS | primary   |
| RESOLVED    | info      |
| CLOSED      | secondary |

### Priority → Bootstrap

| Priority | Class     |
| -------- | --------- |
| LOW      | secondary |
| MEDIUM   | info      |
| HIGH     | warning   |
| CRITICAL | danger    |

Mapping derived from enum values (no hardcoded logic trees).

---

# 🧩 Template Structure

```
ui/templates/issues/
    list.html
    partials/
        issue_row.html
        status_tabs.html
        pagination.html
```

* Extends global base template
* Bootstrap 5
* Clean GitHub-inspired layout
* No SPA
* No heavy JS
* No HTMX (UI-1)

---

# 🚫 Explicitly Out of Scope (UI-1)

* Issue detail page
* Create issue form
* Comment submission
* Status transitions
* Attachment download UI
* Edit/delete actions
* Search
* AJAX / HTMX

This phase is strictly **read-only list view**.

---

# 📦  Deliverable (UI-1)

Visiting:

```
https://issues.localhost:9999/
```

Redirects to:

```
/issues/
```

Result:

* Pagination works
* Status filtering works
* Visibility rules enforced
* Layout aligned with frontend theme
* No console impact
* No modification to `genericissuetracker`
* No architectural leakage

---

# 📘 Phase UI-2 — Requirement Scope (Detail View + Read-Only Discussion)

## 🎯 Objective

Extend the Issue Tracker UI with a **server-rendered Issue Detail Page** that:

* Displays full issue information
* Displays comment thread
* Shows secure attachment links
* Strictly reuses existing domain services
* Introduces zero business-logic duplication

UI-2 remains **read-only** (no create/update yet).

---

# 🧱 What UI-2 Will Deliver

## 1️⃣ Issue Detail View

### 📍 Route

On subdomain:

```
https://issues.<domain>/issues/<uuid>/
```

Namespace:

```python
reverse("issues:detail", kwargs={"pk": issue.pk})
```

---

### 📄 Page Layout

The page will display:

| Section     | Content                                     |
| ----------- | ------------------------------------------- |
| Header      | Issue title + status badge + priority badge |
| Meta Block  | Reporter, created date, last updated        |
| Description | Full issue description                      |
| Attachments | Secure links (if present)                   |
| Comments    | Threaded list (flat rendering for now)      |

---

## 2️⃣ Comment Thread (Read-Only)

* Render all related comments
* Order by created_at ascending
* Display:

  * Author
  * Created time (humanized)
  * Comment content
* No reply form yet (UI-3)

Must reuse existing comment model from `genericissuetracker`.

No filtering logic in template.

---

## 3️⃣ Secure Attachment Handling

Attachments must:

* Use protected download endpoint (already implemented in integration)
* Never expose `.file.url`
* Use:

```python
reverse("issues:attachment_download", kwargs={...})
```

We will verify correct namespacing during implementation.

---

## 4️⃣ Visibility & Permission Enforcement

UI-2 must:

* Use the same `IssueVisibilityService`
* Ensure unauthorized access returns 404 (not 403)
* Never manually check roles

Access pattern:

```python
issue = IssueQueryService.get_single_issue_for_user(user, pk)
```

If not visible → raise `Http404`.

---

## 5️⃣ Template Structure

Inside:

```
ui/templates/issues/detail.html
ui/templates/issues/partials/comment_row.html
ui/templates/issues/partials/attachment_list.html
```

Extends:

```
admin/base.html
```

Styling:

* Bootstrap cards
* Badge styling for status/priority
* GitHub-style issue header layout
* Reuse your theme system

---

## 6️⃣ URL Additions

Inside:

```
ui/urls.py
```

Add:

```python
path("<int:issue_number>/", IssueDetailView.as_view(), name="detail")
```

---

# 🔐 Architectural Rules (Strict)

UI-2 will:

* Import only from:

  * `genericissuetracker.models`
  * `IssueVisibilityService`
* Not duplicate permission classes
* Not modify lifecycle state
* Not perform status transitions
* Not allow comment creation
* Not allow issue edits

Pure presentation layer.

---

# 🧠 Service Layer Extension

We will extend:

```
IssueQueryService
```

Add:

```python
get_issue_for_detail(user, pk)
```

Responsibilities:

* Base queryset
* Visibility filter
* Prefetch comments + attachments
* Deterministic ordering
* Return single object or raise 404

No logic beyond query construction.

---

# 📦 Deliverables After UI-2

After this phase:

* Clicking an issue in list view opens detail page.
* Full discussion visible.
* Attachments downloadable securely.
* Visibility rules respected.
* No write operations exposed.

---

# ✅ UI-2 Validation Checklist

**Feature:** Issue Detail View (Read-Only)
**Branch:** `feature/issue-tracker-integration-ui-2`

---

## 1️⃣ Routing & Navigation

### ✔ Issue list → detail navigation

* Go to:

  ```
  https://issues.localhost:9999/issues/
  ```
* Click any issue title.
* Confirm redirect to:

  ```
  /issues/<issue_number>/
  ```
* Confirm URL uses **issue_number** (not UUID).

### ✔ Back navigation

* Click “← Back to Issues”.
* Confirm:

  * Redirects to `/issues/`
  * Status filter preserved (if applied)

---

## 2️⃣ Visibility Governance (RBAC)

### ✔ Anonymous user

* Log out.
* Visit public issue detail page.
* Confirm:

  * Public issue visible.
  * Internal (is_public=False) issue returns **404**.
  * No 403 should appear.

### ✔ Authenticated non-privileged user

* Login as standard employee (non-internal role).
* Confirm:

  * Public issues visible.
  * Internal issues return **404**.

### ✔ Privileged role (CEO / DJGO / allowed roles)

* Login as privileged user.
* Confirm:

  * Both public and internal issues visible.
  * Comments visible.
  * Attachments downloadable.

---

## 3️⃣ Comment Rendering

For an issue with comments:

* Confirm:

  * Comment count in header matches DB.
  * `commenter_email` is displayed.
  * `comment.body` is visible.
  * Timestamp uses `naturaltime`.
  * Comments ordered ascending (oldest first).

For issue without comments:

* Confirm:

  * “No comments yet.” message appears.

---

## 4️⃣ Attachment Handling

For issue with attachments:

* Confirm:

  * Attachment list appears.
  * File name shown correctly.
  * Download link points to:

    ```
    /api/v1/issuetracker/attachments/<uuid>/download/
    ```
  * Clicking download works.
  * Unauthorized access returns 404.

Confirm:

* No direct MEDIA URL exposed.
* No `.file.url` used in templates.

---

## 5️⃣ Soft Delete Safety

* Soft delete an issue.
* Attempt to access detail page.
* Confirm:

  * Returns 404.
  * No data leakage.

---

## 6️⃣ Data Integrity

Inspect rendered page and confirm:

* Reporter uses `reporter_email`
* Comment uses `body`
* Status badge displays correct value
* Priority badge displays correct value
* Issue number displayed in header

---

## 7️⃣ No Regression in UI-1

Re-test:

* Issue list page loads.
* Pagination works.
* Status filtering works.
* Comment count still visible.
* Lock icon shows for internal issues.

---

## 8️⃣ No Business Logic Duplication

Manual code review confirmation:

* No permission logic in templates.
* No manual role checks in views.
* Only `IssueVisibilityService` used.
* No direct access to raw MEDIA.
* No schema mutation.

---

# 📦 Expected State After UI-2

System now supports:

* GitHub-style issue list
* GitHub-style issue detail
* Read-only comments
* Secure attachment downloads
* Full RBAC visibility governance
* 404 masking for unauthorized access

No write operations exposed in UI yet.

---

# ✅ 📘 UI-3 — **Updated  Scope**

Branch:

```bash
feature/issue-tracker-integration-ui-3
```

---

# 🎯 Phase Goal (Achieved)

Introduce controlled write operations into Issue Detail UI:

1. Add Comment (anonymous + authenticated)
2. Change Issue Status (policy-driven lifecycle)
3. Proper domain lifecycle delegation
4. Signal-based audit consistency
5. No duplication of lifecycle rules

---

# 🧱 1️⃣ Add Comment From UI

### Location

```
/issues/<issue_number>/
```

---

## ✅ Visibility Rules (Implemented)

| User Type           | Comment Allowed?                                                |
| ------------------- | --------------------------------------------------------------- |
| Anonymous           | ✅ Only if `GENERIC_ISSUETRACKER_ALLOW_ANONYMOUS_REPORTING=True` |
| Anonymous           | ❌ Blocked for internal issues                                   |
| Authenticated       | ✅ Yes (any issue visible to them)                               |
| Invalid login state | ❌ Blocked                                                       |
| Soft-deleted        | ❌ Blocked via identity validation                               |

---

## ✅ Behavior

* POST → same URL
* `action=add_comment`
* Anonymous requires email
* Authenticated email resolved via `get_identity_resolver()`
* Emits `issue_commented` signal
* Audit logged via integration signals
* PRG redirect enforced
* Structured result handling via service layer

---

## ✅ Architecture

```
ui/services/issue_mutation_service.py
```

### add_comment()

* Identity resolved via `get_identity_resolver()`
* Anonymous internal-issue safeguard added
* Creates `IssueComment`
* Emits `issue_commented`
* No serializer reuse
* No lifecycle duplication

---

# 🔐 2️⃣ Status Change From UI

### Location

Near status badge in header

---

## ✅ Visibility Rules

| User Type                            | Status Change Allowed?       |
| ------------------------------------ | ---------------------------- |
| Anonymous                            | ❌                            |
| Authenticated                        | Depends on transition policy |
| Superuser                            | ✅                            |
| Role in `ISSUE_STATUS_ALLOWED_ROLES` | ✅                            |
| Other roles                          | ❌                            |

---

## ✅ Behavior

* POST → same URL
* `action=change_status`
* Delegates to:

```python
change_issue_status(issue, new_status, identity)
```

* Lifecycle engine enforces:

  * Transition map
  * Transition policy
  * Status history creation
  * Atomic DB write
  * Signal emission
* PRG redirect

---

## 🚨 Important Correction from Original Scope

Original scope mentioned:

> Update issue.status manually and emit signal

That was incorrect architecturally.

Implementation:

✔ Delegates entirely to lifecycle engine
✔ Does NOT duplicate transition validation
✔ Does NOT manually emit `issue_status_changed`

This is the correct enterprise approach.

---

# 🧭 View Strategy 

`IssueDetailView` handles:

```python
if action == "add_comment":
    IssueMutationService.add_comment(...)
elif action == "change_status":
    IssueMutationService.change_status(...)
```

* No new routes
* No fragmented mutation endpoints
* Thin orchestration only

---

# 🛡 Security Guarantees 

✔ Visibility still enforced via `IssueVisibilityService`
✔ Internal issues masked via 404
✔ Anonymous cannot comment on internal issues
✔ Lifecycle policy enforced centrally
✔ Transition policy injected via integration
✔ Signals power audit layer
✔ PRG pattern enforced
✔ No role logic in templates
✔ No business logic in templates

---

# 🚫 Still Explicitly Not Included

* Attachment upload from UI
* Edit issue
* Delete issue
* Delete comment
* Label editing
* AJAX transitions

---

# 🏁 UI-3  Architecture State

| Concern                        | Status |
| ------------------------------ | ------ |
| Domain lifecycle enforcement   | ✅      |
| Policy RBAC                    | ✅      |
| UI mutation thin orchestration | ✅      |
| Audit integration              | ✅      |
| Anonymous governance           | ✅      |
| 404 masking                    | ✅      |
| Attachment security            | ✅      |

UI-3 is structurally sound.

---

# 📘 UI-4 — Issue Creation, Comment Length, Attachment policy in Issue and Comment creation

---

Branch:

```
feature/issue-tracker-integration-ui-4
```
---

# 🎯 Release Objective

Deliver complete write-capable Issue Tracker UI with:

1. Issue creation (public + internal with RBAC)
2. Attachment support (issue + comment level)
3. Comment length governance
4. Role-governed internal issue creation
5. Strict DRY reuse of library validation
6. PRG (Post-Redirect-Get) discipline
7. Unified Django message rendering
8. Standardized timestamp formatting
9. Production-level UI consistency

---

# 🧱 Functional Scope

---

## 1️⃣ Issue Creation UI

### Route

```
/issues/new/
```

### Capability Matrix

| User Type                        | Can Create Public Issue | Can Create Internal Issue |
| -------------------------------- | ----------------------- | ------------------------- |
| Anonymous                        | ✔ (if setting enabled)  | ❌                         |
| Authenticated (role allowed)     | ✔                       | ✔                         |
| Authenticated (role not allowed) | ✔                       | ❌                         |
| Soft-deleted user                | ❌ (resolver governed)   | ❌                         |

---

### Enforcement Location

Internal issue governance enforced in:

```
IssueMutationService.create_issue()
```

Not:

* Not in template
* Not in serializer
* Not in view
* Not in library

Library remains role-agnostic.

---

## 2️⃣ Attachment Support

### During Issue Creation

* Multiple attachments allowed
* MAX_ATTACHMENTS enforced by library
* MAX_ATTACHMENT_SIZE_MB enforced by library
* Atomic behavior reused from `IssueCreateSerializer`

---

### From Detail Page

| Scenario                      | Allowed |
| ----------------------------- | ------- |
| Anonymous → public issue      | ✔       |
| Anonymous → internal issue    | ❌       |
| Authenticated → visible issue | ✔       |
| Invisible issue               | ❌       |
| Soft deleted issue            | ❌       |

Enforced via:

* Visibility service
* Identity resolver
* Library validation

---

## 3️⃣ Comment Length Governance

Setting:

```python
GENERIC_ISSUETRACKER_MAX_COMMENT_LENGTH = 5000
```

Enforced via:

```python
get_setting("MAX_COMMENT_LENGTH")
```

UI:

```html
maxlength="5000"
```

No duplication of validation logic.

---

## 4️⃣ Timestamp Standardization

Implemented reusable partial:

```
templates/issues/partials/timestamp.html
```

Behavior:

* Visible: formatted IST datetime
* Tooltip: relative time (naturaltime)
* Uses Django timezone framework
* Works with USE_TZ=True
* DRY reuse across issue + comments

Usage:

```django
{% include "issues/partials/timestamp.html" with value=issue.created_at %}
```

Applied to:

* Issue header timestamp
* Comment timestamps

---

## 5️⃣ Django Messages System Standardization

### Problem Solved

* Bootstrap 5 mismatch (`alert-error` → `alert-danger`)
* Duplicate message rendering
* Black flicker row
* Missing success messages

### Final Architecture

* Single message rendering location: `admin/base.html`
* Custom template filter:

```
frontend/templatetags/django_message_utils.py
```

```python
@register.filter
def bootstrap_alert(level):
    mapping = {
        "error": "danger",
        "warning": "warning",
        "success": "success",
        "info": "info",
    }
```

### Base Template Rendering

```django
{% if messages %}
    {% for message in messages %}
        <div class="alert alert-{{ message.level_tag|bootstrap_alert }} alert-dismissible fade show">
            {{ message }}
        </div>
    {% endfor %}
{% endif %}
```

Guarantees:

* Correct Bootstrap mapping
* No duplicate rendering
* PRG success messages visible
* No layout flicker

---

# 🏗 Architecture Principles Enforced

✔ Library validation reused
✔ No domain duplication
✔ No lifecycle duplication
✔ No business logic in templates
✔ No RBAC logic in serializers
✔ Role-based internal governance
✔ PRG discipline everywhere
✔ Signals preserved
✔ Visibility masking preserved
✔ Soft delete masking preserved
✔ DRY timestamp rendering
✔ DRY message rendering

---

# 🚫 Explicitly Not Included

* Edit issue
* Delete issue
* Delete attachment
* AJAX
* Label system
* API modifications
* Library refactor
* Dynamic navigation system

---

# 🧪 Validation Checklist (UI-4)

---

# 1️⃣ Issue Creation

### Anonymous Public Issue

* [ ] Email field visible
* [ ] Cannot submit without email
* [ ] Issue created successfully
* [ ] Redirect to detail (PRG)
* [ ] Success message visible once
* [ ] Reporter email saved correctly
* [ ] Attachments saved

---

### Anonymous Internal Issue

* [ ] Blocked
* [ ] Error message styled correctly
* [ ] No DB record created

---

### Authenticated Public Issue

* [ ] Email auto-filled
* [ ] Email not editable
* [ ] Issue created successfully
* [ ] Spoof attempt ignored
* [ ] Redirect works

---

### Authenticated Internal Issue (Allowed Role)

* [ ] Internal issue created
* [ ] Visible only to allowed roles
* [ ] Not visible to unauthorized users

---

### Authenticated Internal Issue (Disallowed Role)

* [ ] Blocked
* [ ] Proper error message
* [ ] No DB write

---

# 2️⃣ Attachment Validation

### During Issue Creation

* [ ] Single attachment works
* [ ] Multiple attachments work
* [ ] Exceed MAX_ATTACHMENTS blocked
* [ ] Exceed MAX_ATTACHMENT_SIZE blocked
* [ ] Signals emitted once per file

---

### From Detail Page

* [ ] Public issue attachment works
* [ ] Anonymous cannot attach to internal
* [ ] Invisible issue blocked
* [ ] Soft deleted issue blocked

---

# 3️⃣ Comment Validation

* [ ] Comment-only works
* [ ] Attachment-only works
* [ ] Empty submission blocked
* [ ] Length > 5000 blocked
* [ ] Anonymous email required
* [ ] Authenticated uses identity resolver
* [ ] PRG redirect
* [ ] Success message visible

---

# 4️⃣ Timestamp Validation

* [ ] Issue header shows IST formatted time
* [ ] Tooltip shows relative time
* [ ] Comment timestamps consistent
* [ ] No duplicate bullets
* [ ] Works with timezone enabled

---

# 5️⃣ Django Message System

* [ ] Success message shown once
* [ ] No duplicate messages
* [ ] No black flicker row
* [ ] Error messages styled as red
* [ ] Warning/info styled correctly
* [ ] No inline style hacks
* [ ] Messages cleared after one request

---

# 6️⃣ Security Validation

* [ ] Internal issue escalation prevented
* [ ] Reporter spoofing prevented
* [ ] Attachment RBAC enforced
* [ ] Soft delete respected
* [ ] Visibility masking respected
* [ ] Transition policy intact

---

# 7️⃣ Regression (UI-1 → UI-3)

* [ ] List filters intact
* [ ] Status change works
* [ ] Pagination intact
* [ ] Visibility filtering intact
* [ ] No signal duplication
* [ ] No media leak

---

# 🏁 Release Readiness Criteria

UI-4 is complete if:

✔ All checklist items pass
✔ No template duplication
✔ No RBAC bypass
✔ No double message rendering
✔ No broken Bootstrap classes
✔ No duplicate DB writes
✔ No 500 errors
✔ PRG discipline intact

---
