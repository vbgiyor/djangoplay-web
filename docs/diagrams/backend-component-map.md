## 📁 Django backend Component Map for PayStream project

---

### 📁 backend\_paystream/

```
├── 📁 paystream/                    # Main Django project folder
│   ├── __init__.py
│   ├── settings.py                  # Django settings with Redis, Celery config, DRF, CORS, etc.
│   ├── urls.py                      # Root URL routes including API and admin
│   ├── wsgi.py
│   ├── asgi.py
│   └── celery.py                    # Celery app instance and config for task queue
│
├── 📁 clients/                     # Django app for Client management
│   ├── __init__.py
│   ├── admin.py                    # Client model admin registration
│   ├── apps.py
│   ├── models.py                   # Client data model
│   ├── serializers.py              # DRF serializers for Client
│   ├── views.py                    # API views (ViewSets/Generic Views) for Client CRUD
│   ├── urls.py                     # App-level URLs for client endpoints
│   ├── permissions.py              # Custom DRF permissions (if any)
│   ├── tests.py                    # Unit and integration tests for clients app
│   └── migrations/
│       └── ...
│
├── 📁 invoices/                    # Django app for Invoice and PDF handling
│   ├── __init__.py
│   ├── admin.py                    # Invoice model admin registration
│   ├── apps.py
│   ├── models.py                   # Invoice model, PDF file field, status, relations
│   ├── serializers.py              # DRF serializers for Invoice
│   ├── views.py                    # API views for invoice CRUD, upload endpoints
│   ├── urls.py                     # App-level URLs for invoice endpoints
│   ├── permissions.py              # Invoice-specific permissions
│   ├── tasks.py                   # Celery tasks (e.g., async invoice processing)
│   ├── tests.py                    # Tests for invoice app
│   └── migrations/
│       └── ...
│
├── 📁 audit/                       # Audit logging app (optional but recommended)
│   ├── __init__.py
│   ├── admin.py
│   ├── models.py                   # Audit log model (user, action, timestamp, entity)
│   ├── serializers.py
│   ├── views.py                   # API view for fetching audit logs
│   ├── urls.py
│   ├── permissions.py
│   ├── signals.py                 # Django signals to log actions on client/invoice models
│   ├── tests.py
│   └── migrations/
│       └── ...
│
├── 📁 users/                      # Custom user/auth app (if using custom User model)
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py                  # Custom User model (optional)
│   ├── serializers.py
│   ├── views.py                   # Registration, login, logout API views
│   ├── urls.py
│   ├── permissions.py
│   ├── tokens.py                  # JWT token utilities (if any)
│   ├── tests.py
│   └── migrations/
│       └── ...
│
├── manage.py                      # Django CLI entry point
│
├── requirements.txt               # Python dependencies (Django, DRF, Celery, Redis, etc.)
│
├── Dockerfile                    # Dockerfile to containerize backend
│
├── docker-compose.yml            # Docker compose config (backend, Redis, Celery workers)
│
├── celeryconfig.py               # Optional separate celery configuration
│
├── README.md                     # Project documentation and setup instructions
```

---

### Summary of key backend modules:

* **paystream/settings.py**: Core Django config including Redis, Celery broker, DRF config, CORS, allowed hosts, DB setup.
* **paystream/celery.py**: Celery app definition with Redis broker and task imports.
* **clients/**: Client model, CRUD API with serializers and views.
* **invoices/**: Invoice model with PDF file handling, upload endpoints, Celery tasks for async processing.
* **audit/**: Audit log model and signals to track create/update/delete events.
* **users/**: Custom user management, registration, authentication with JWT.
* **docker-compose.yml**: Runs Django backend, Redis, and Celery workers together for async tasks.
* **tests.py** in each app: Unit tests for models, views, and APIs.

---