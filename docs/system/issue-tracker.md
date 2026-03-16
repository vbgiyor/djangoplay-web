# Issue Tracker Integration

DjangoPlay integrates **genericissuetracker**:

* Repository: [https://gitlab.com/binaryfleet/issuetracker](https://gitlab.com/binaryfleet/issuetracker)
* License: MIT
* Type: Reusable, versioned Django Issue Tracker
* Stack: Django + DRF + drf-spectacular

---

## Subdomain Architecture

The Issue Tracker UI is mounted on a **dedicated subdomain**.

Example (local development):

```
http://issues.localhost:8000/issues/
```

Accessing from a non-issues host returns **404**.

**Why subdomain isolation?**

* Clear architectural boundary
* No route pollution in primary domain
* Security segmentation
* Future external/public exposure capability
* Independent scaling potential

IssueTracker UI must **not** be mounted under the main domain.

---

## Integration Architecture

Starting in **v1.1.0**, DjangoPlay introduces a convergence layer between the
internal Helpdesk system and the IssueTracker domain. Bug reports and support
requests now synchronize with IssueTracker through a dedicated adapter layer.

```
GenericIssueTracker (Library)
        │
        ▼
DjangoPlay Integration Layer
        │
        ├── Identity Resolver
        ├── Transition Policy
        ├── Visibility Governance
        ├── Issue Mutation Service
        ├── Issue Timeline Service
        ├── Label Bootstrap
        ├── Secure Attachment Streaming
        │
        ▼
Helpdesk Compatibility Layer
        │
        ├── BugReport Adapter
        └── SupportTicket Adapter
        │
        ▼
DjangoPlay UI (issues.<domain>)
```

---

## Key Integration Components

### Identity Boundary

Configured via `GENERIC_ISSUETRACKER_IDENTITY_RESOLVER`.
No direct dependency on Django's default User model.

### Transition Policy

Configured via `GENERIC_ISSUETRACKER_TRANSITION_POLICY`. Supports superuser
override, owner override, and role-based governance.

### Visibility Governance

Implemented via `IssueVisibilityService` — superuser bypass, role-based
filtering, queryset-level enforcement, and 404 masking.

### Audit Integration

Mapped domain signals: `issue_created`, `issue_updated`, `issue_deleted`,
`issue_status_changed`, `issue_commented`, `attachment_uploaded`,
`attachment_deleted`. Append-only. Failure-safe. No foreign keys.

### UI Layer

* Server-rendered list and detail views
* Anonymous and authenticated issue creation
* Comment and attachment support
* Status transition form
* IST timestamp formatting with naturaltime tooltip
* PRG pattern enforced
* Unified issue activity timeline (status history, comments, attachments)

### Upgrade Safety

All custom logic exists in `paystream.integrations.issuetracker`.
The third-party library remains untouched, guaranteeing safe upgrades.