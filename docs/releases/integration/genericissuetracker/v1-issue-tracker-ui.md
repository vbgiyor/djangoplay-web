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
* Final UI polish

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

# 📦 Final Deliverable (UI-1)

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
