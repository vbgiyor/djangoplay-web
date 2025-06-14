## 📁 PayStream Architecture Layout


* Client browser → NGINX proxy → React frontend + Django backend + DB
* Docker Compose orchestration
* Redis as broker + cache/session store
* Celery worker + Celery Beat for async and scheduled tasks
* AWS S3 for private PDF storage with signed URLs

---

```
          ┌───────────────────────────┐
          │      Client Browser       │
          └────────────┬──────────────┘
                       │ HTTP/HTTPS
                       ▼
          ┌───────────────────────────┐
          │        NGINX Proxy        │
          │ - Serves React static     │
          │ - Proxies API requests to │
          │   Django backend          │
          └────────────┬──────────────┘
                       │
                       ▼
         ┌────────────────────────────────────────┐
         │      Docker Compose Orchestrator       │
         │                                        │
         │  ┌─────────────────────────────┐       │
         │  │ React Frontend (SPA)        │       │
         │  │ (served via NGINX static)   │       │
         │  └─────────────────────────────┘       │
         │                                        │
         │  ┌──────────────────────────────┐      │
         │  │ Django Backend               │      │
         │  │ (Gunicorn + DRF REST API)    │      │
         │  │ - Uses Redis (broker/cache)  │      │
         │  │ - Connects to PostgreSQL DB  │      │
         │  │ - Connects to AWS S3 for PDFs│      │
         │  └────────────┬─────────────────┘      │
         │               │                        │
         │               ▼                        │
         │        ┌────────────────┐              │
         │        │    Redis       │              │
         │        │ (Broker, Cache │              │
         │        │  Session Store)│              │
         │        └──────┬─────────┘              │
         │               │                        │
         │      ┌────────▼─────────┐              │
         │      │   Celery Worker  │              │
         │      │ Async Tasks      │              │
         │      └────────┬─────────┘              │
         │               │                        │
         │       ┌───────▼───────┐                │
         │       │   Celery Beat │ Scheduled tasks│
         │       └───────────────┘                │
         │                                        │
         │  ┌─────────────────────────────┐       │
         │  │     PostgreSQL Database     │       │
         │  │ Persistent storage for data │       │
         │  └─────────────────────────────┘       │
         │                                        │
         │  ┌─────────────────────────────┐       │
         │  │         AWS S3 Storage      │       │
         │  │ Private PDF storage +       │       │
         │  │ signed URL generation       │       │
         │  └─────────────────────────────┘       │
         └────────────────────────────────────────┘
```

### More graphical representation: - [📊 Architecture](ArchitectureDiagram.svg)
---

### Key Features & Responsibilities

**Django Core:**

* Manages the main backend logic, including URL routing, middleware, and global settings.

**Apps:**

* **Clients:** Handles client data models, serializers, views (CRUD APIs), and business logic.
* **Invoices:** Manages invoice models, including CRUD operations, PDF file handling, and status workflows.
* **Audit:** Records user actions and system events asynchronously for compliance and traceability.
* **Users/Auth:** Custom user model, JWT-based authentication, and role-based permission enforcement.

**Celery & Redis:**

* Provides asynchronous task queue management (email sending, audit logging, PDF processing).
* Redis acts as Celery broker and optional cache/session store.

**PostgreSQL Database:**

* Persistent relational storage for all models (clients, invoices, users, audit logs).

**AWS S3 Integration:**

* Secure, private storage of uploaded invoice PDFs with signed URL access for downloads.

**Settings & Configuration:**

* Centralized environment-based settings with support for secrets, debug flags, CORS, and third-party integrations.

**Docker & Orchestration:**

* Containerized deployment environment, orchestrated with Docker Compose for consistent multi-service startup.

---
