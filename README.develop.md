# 💰 DjangoPlay

**DjangoPlay** is a modular, enterprise-grade backend platform built with **Django and Django REST Framework**, designed to power business-critical systems such as **identity management, invoicing, financial data, entities, and locations**.

It is engineered with **clean architecture, strict separation of concerns, and long-term scalability** in mind, while remaining fully functional as a monolith.

---

## 🧾 What Is DjangoPlay?

DjangoPlay is a **backend-first platform** that provides:

* Identity & access management
* Financial and invoicing workflows
* Business entity modeling
* Location and industry hierarchies
* API documentation and observability
* Admin console for operational control

The platform is intentionally structured to support **future service extraction** (microservices) without requiring a rewrite.

---

## ✨ Key Features

### 🔐 Identity & Access

* Employees and Members
* Role-based access control
* Departments, teams, and permissions
* Manual and SSO onboarding
* Password reset and verification flows

### 🧾 Invoicing & Finance

* Invoices, payments, and billing schedules
* Line items and GST configuration
* Tax profiles and business contacts
* Status lifecycle management
* Historical tracking

### 🏢 Business Domains

* Entities (businesses)
* Industries (classification)
* Locations (global regions, countries, cities, timezones)

### 📊 APIs & Observability

* Versioned REST APIs (v1)
* Read / write serializer separation
* Swagger & Redoc documentation
* API request logging and statistics

### 🧰 Platform Infrastructure

* Centralized settings and middleware
* Custom Django Admin console
* Rate limiting and throttling
* Email workflows (verification, reset, support)
* Background task scaffolding

---

## ⚙️ Tech Stack

| Layer         | Technology                                         |
| ------------- | -------------------------------------------------- |
| Backend       | Django, Django REST Framework                      |
| Auth          | Django Sessions, JWT (extensible), Allauth         |
| Database      | PostgreSQL                                         |
| Async         | Celery, Redis                                      |
| API Docs      | drf-spectacular, Swagger, Redoc                    |
| Admin         | Custom Django AdminSite                            |
| Storage       | Local (dev), AWS S3 ready                          |
| Observability | Structured logging, request tracing                |
| Frontend      | Server-rendered templates (React optional, future) |

---

## 🏗️ High-Level Architecture

DjangoPlay is organized into **clear application layers**, each with a distinct responsibility.

### Core Platform

* Central settings
* Middleware
* Permissions
* Lifecycle and audit base models

### Identity & Experience

* `users`
* `frontend`
* `apidocs`

### Business Domains

* `locations`
* `industries`
* `fincore`
* `entities`
* `invoices`

### Infrastructure & Shared Kernel

* `utilities` (shared helpers, API base classes)
* Background tasks and operational tooling

---

## 📁 Project Structure (Simplified)

```text
django_play/
├── core/           # Platform core (models, middleware, permissions)
├── users/          # Identity & access management
├── frontend/       # Auth flows, templates, UI pages
├── apidocs/        # Swagger, Redoc, API stats
├── locations/      # Geo hierarchy and timezone data
├── industries/     # Industry classification
├── fincore/        # Financial core (addresses, contacts, tax)
├── entities/       # Business entities
├── invoices/       # Invoicing and billing workflows
├── utilities/      # Shared kernel and infrastructure helpers
├── policyengine/   # Role & permission rules
├── paystream/      # Project settings and runtime config
└── manage.py
```

> **Note**: Each domain app follows a consistent structure:
>
> * `models`
> * `serializers/base` and `serializers/v1`
> * `views/v1` (read / write / history / list / detail)
> * `permissions`, `signals`, and tests

---

## 🧠 Architectural Principles

DjangoPlay follows these non-negotiable principles:

1. **Separation of Concerns**

   * Domain logic stays in domain apps
   * Infrastructure stays isolated
   * UI and backend responsibilities are clear

2. **Explicit Ownership**

   * Each app owns its data and logic
   * Cross-app imports are intentional and controlled

3. **Versioned APIs**

   * All APIs are versioned (`v1`)
   * Read and write serializers are separated

4. **Monolith First, Services Ready**

   * Runs as a single Django project
   * Designed to extract services later without rewriting

---

## 🧱 Centralized Core Models

Shared base models and managers live in the `core` app.

### Why?

* Single source of truth
* No duplication
* Cleaner domain apps

### Examples

* `TimeStampedModel`
* `SoftDeletableModel`
* `ActiveManager`
* Audit and lifecycle helpers

These are imported and reused across all domain apps.

---

## 🛠️ Setup (Development)

```bash
git clone <repo-url>
cd django_play
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

## 📦 API Documentation

* Swagger: `/api/docs/swagger/`
* Redoc: `/api/docs/redoc/`
* OpenAPI schema: `/api/schema/`

---

## 🧪 Testing

* Django test suite per app
* Concurrency and validation tests included
* Additional coverage planned

```bash
python manage.py test
```

---

## 🚧 Roadmap (High Level)

* Email infrastructure isolation
* Centralized audit logging
* Dependency inversion around identity
* Service extraction readiness
* Observability integrations (Grafana / Sumo Logic)

---

## 📘 Contributing

Please see [`CONTRIBUTING.md`](CONTRIBUTING.md) for:

* Development guidelines
* Code style
* Branching strategy
* Pull request process

---

## 📜 License

MIT License

---

## 🙌 Acknowledgements

* Designed from real-world enterprise and SMB requirements
* Inspired by long-running Django systems that value stability over hype
* Built with a strong focus on maintainability and clarity

---
