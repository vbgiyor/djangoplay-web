
# 🧠 3️⃣ DRY + Proper Django Architecture Strategy (Important)

Now the critical part — design correctness.

You correctly stated:

> UI must not duplicate business logic.

Here is the proper layered architecture we will follow:

---

## 🔷 Final Architecture (Strictly DRY)

```
issues_ui (Presentation Layer)
        ↓
Service Adapter Layer (thin integration wrapper)
        ↓
genericissuetracker (Domain Logic)
        ↓
RBAC + Audit + Signals (already complete)
```

---

## 🚫 What We Will NOT Do

* ❌ No HTTP calls to `/api/v1/issuetracker/`
* ❌ No duplicated permission checks
* ❌ No re-implementing visibility logic
* ❌ No direct MEDIA exposure
* ❌ No business rules inside templates

---

## ✅ Correct Integration Pattern

Inside `issues_ui`:

### views.py

Only:

* Call visibility service
* Call permission class
* Call existing transition service
* Render template

Example pattern (conceptual only):

```python
class IssueListView(LoginRequiredMixin, TemplateView):
    template_name = "issues/list.html"

    def get_queryset(self):
        return IssueVisibilityService.get_visible_issues(self.request.user)
```

This ensures:

* Single source of truth
* UI stays thin
* Domain logic centralized

---

# 🏗 4️⃣ Subdomain Routing Strategy (Future-Proof)

For now:

```
/issues/
```

Later, production Nginx config:

```
server_name issues.djangoplay.com;

location / {
    proxy_pass http://django_app;
}
```

Inside Django:

```python
if request.get_host().startswith("issues."):
    include("issues_ui.urls")
```

Or cleaner:

Use Django `Site` object routing.

We will implement that in UI-4.

---

# 🧱 5️⃣ Final Clean Implementation Roadmap (Locked)

We will strictly follow this order:

### UI-1

* issues_ui app
* urls.py
* ListView
* Pagination
* Status filter

### UI-2

* DetailView
* Comment thread
* Attachment secure links

### UI-3

* CreateView
* Comment form
* Status change form
* Django messages integration

### UI-4

* Subdomain binding
* Production routing
* Final UI polish

---

# 🔒 6️⃣ Security Guarantees

UI layer will:

* Never query `.all()` directly
* Always go through visibility service
* Use existing permission classes
* Use signed URLs for attachments
* Respect EmploymentStatus.ACTV requirement

We will treat `issues_ui` strictly as presentation.

---

# 🌐 Subdomain Confirmation

You already configured:

```
127.0.0.1 issues.localhost
```

Your `devssl()` already generates certificates including:

```
mkcert localhost issues.localhost 127.0.0.1 ::1
```

✅ You DO NOT need new certificates.
Your script already supports `issues.localhost`.

The only required change will be:

```bash
export SITE_HOST=issues.localhost
```

instead of `localhost` when you want to run the issues subdomain locally.

Your SSL + mkcert setup is already correct.

---

Now let’s redefine UI-1 properly.

---

# 🌿 Git Branch

```
feature/issue-tracker-integration-ui-1
```

---

# 📘 Phase UI-1 — Architecture Scope (Enterprise-Aligned)

---

## 🎯 Objective

Introduce a **server-rendered UI layer** for the third-party library:

```
genericissuetracker
```

Integrated into DjangoPlay (Paystream), mounted exclusively on:

```
https://issues.localhost:9999/issues/
```

And in production:

```
https://issues.djangoplay.com/issues/
```

This phase delivers:

* Subdomain-aware routing
* Integration-bound UI module (not a new domain app)
* GitHub-style Issue List page
* Status filtering (ALL statuses from enum)
* Pagination (library-config driven)
* Strict reuse of visibility governance
* Zero duplication of permission/business logic
* Zero modification to genericissuetracker core

---

# 🧱 Architectural Placement

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

This respects your established pattern:

```
app/
    models/
    serializers/
    views/
    services/
    permissions.py
    signals.py
    ui/
```

We are extending the **integration layer**, not creating:

* ❌ A new domain
* ❌ A shadow Issue model
* ❌ A duplicate permission system
* ❌ A second lifecycle engine

---

# 🧠 Architectural Principles Applied

---

## 1️⃣ Third-Party Boundary Respect

The Issue model and enums are imported strictly from:

```python
from genericissuetracker.models import Issue, IssueStatus, IssuePriority
```

Never from:

```python
paystream.integrations.issuetracker.models  ❌
```

We treat `genericissuetracker` as an immutable, reusable library.

All UI logic is a consumer of its public contract.

---

## 2️⃣ Integration Cohesion

The UI belongs inside the integration because:

* It renders `Issue` objects
* It depends on visibility governance implemented during backend phases
* It must respect IssueTrackerAccessPermission rules
* It must align with lifecycle policy and identity resolver behavior

Keeping UI inside the integration prevents domain leakage.

---

## 3️⃣ Thin Views

Location:

```
ui/views/read/issue_list.py
```

Responsibilities:

* Parse query parameters
* Call IssueQueryService
* Handle pagination
* Render template

It must NOT:

* Contain filtering logic
* Contain role checks
* Call lifecycle services
* Apply business rules
* Reimplement visibility filtering

---

## 4️⃣ Query Responsibility in Service Layer

Location:

```
ui/services/issue_query_service.py
```

Responsibilities:

* Construct base queryset using:

  ```python
  Issue.objects.all()
  ```

  (Soft delete automatically respected via default manager)

* Apply visibility filtering using existing integration visibility service

* Apply enum-driven status filtering

* Apply deterministic ordering

* Return clean queryset

This makes logic reusable for:

* UI-2 (detail page)
* UI-3 (dashboard widgets)
* Future search features

---

## 5️⃣ Subdomain Isolation

Routing logic in main `urls.py`:

If:

```python
request.get_host().startswith("issues.")
```

→ Load Issue UI routes only

Else:

→ Load normal Paystream routes

This ensures:

* Console stays isolated
* API stays isolated
* Issue UI cannot accidentally render on main domain
* Security surface remains bounded

---

# 🌐 Subdomain Behavior (UI-1)

| Host                  | Route Behavior          |
| --------------------- | ----------------------- |
| issues.localhost      | UI routes only          |
| localhost             | Normal Paystream routes |
| issues.djangoplay.com | UI routes only          |

---

## Root Behavior (Subdomain Only)

Visiting:

```
https://issues.localhost:9999/
```

Redirects to:

```
/issues/
```

This redirect only applies to `issues.*` hosts.

---

# 🏗 What UI-1 Implements

---

## 1️⃣ URL Endpoints (Subdomain Only)

| URL        | Behavior              |
| ---------- | --------------------- |
| `/`        | Redirect → `/issues/` |
| `/issues/` | Issue List Page       |

No other endpoints in this phase.

---

## 2️⃣ Issue List Page Requirements

### Query Parameters

Supported:

```
/issues/?status=ALL
/issues/?status=OPEN
/issues/?status=IN_PROGRESS
/issues/?status=RESOLVED
/issues/?status=CLOSED
```

Rules:

* Default if omitted → ALL

* Values must be derived from:

  ```python
  IssueStatus.choices
  ```

* No hardcoded string literals

Invalid values → fallback to ALL

---

## 3️⃣ Query Flow (Strict DRY Enforcement)

```
IssueListView
    ↓
IssueQueryService.get_issues_for_list(request.user, status)
    ↓
Issue.objects.all()
    ↓
VisibilityService.filter_queryset(...)
    ↓
Apply enum status filter
    ↓
order_by("-created_at")
```

View must not perform filtering directly.

---

## 4️⃣ Pagination

Must use library-configured page size:

```
GENERIC_ISSUETRACKER_PAGE_SIZE
```

Never hardcode.

Implementation:

```python
from genericissuetracker.services.pagination import resolve_page_size
```

Pagination must be Django Paginator (UI context), but page size derived from library configuration.

---

## 5️⃣ UI Rendering Requirements

Each issue row must display:

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

### Status Color Mapping

| Status      | Bootstrap Class |
| ----------- | --------------- |
| OPEN        | success         |
| IN_PROGRESS | primary         |
| RESOLVED    | info            |
| CLOSED      | secondary       |

Derived from enum value, not hardcoded logic branches.

### Priority Mapping

| Priority | Bootstrap Class |
| -------- | --------------- |
| LOW      | secondary       |
| MEDIUM   | info            |
| HIGH     | warning         |
| CRITICAL | danger          |

---

# 🎨 Layout Requirements

GitHub-inspired:

* White background
* Clean bordered list rows
* Compact spacing
* Status filter nav pills
* Pagination footer
* Bootstrap 5
* Extend existing base template
* No SPA
* No heavy JS
* No HTMX (UI-1)

---

# 🔐 Security Guarantees (UI-1)

UI must:

* Always use integration visibility service
* Never manually filter `is_public`
* Never check roles directly
* Never expose file paths
* Never bypass permission classes
* Never replicate lifecycle validation
* Never mutate Issue model
* Never modify genericissuetracker

---

# 🚫 Explicitly NOT Included in UI-1

* Issue detail page
* Create issue form
* Comment submission
* Status change dropdown
* Attachment download UI
* Edit/delete actions
* Search
* AJAX
* HTMX
* Transition handling

This phase is strictly read-only list view.

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

Templates extend global base template.

No duplication of layout components.

---

# 🧠 Django Design Principles Observed

✔ Third-party library boundary respected
✔ Integration cohesion preserved
✔ Thin views
✔ Service-layer abstraction
✔ Enum-driven filtering
✔ Subdomain isolation
✔ No permission duplication
✔ No lifecycle duplication
✔ No schema mutation
✔ Soft-delete automatically respected
✔ Config-driven pagination

---

# 📦 Deliverable After UI-1

After completion:

Visiting:

```
https://issues.localhost:9999/
```

→ Redirects to:

```
/issues/
```

Issue list renders:

* Pagination works
* Status filtering works
* Visibility rules enforced
* Layout matches frontend theme
* No impact to console
* No modification to genericissuetracker
* No new domain created
* No architectural leakage

---
