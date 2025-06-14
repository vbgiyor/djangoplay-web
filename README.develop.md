
# 💰 PayStream

A modern, full-stack **PayStream** built with **Django + React**. Designed for small businesses and freelancers to manage clients, invoices, payments, and uploaded PDFs—securely, intuitively, and efficiently.

---

## 🧾 Project Idea: PayStream

**PayStream** is a application for managing:

- ✅ Clients: Add, edit, delete, search clients.
- 🧾 Invoices: Create, update, delete invoices; associate them with clients.
- 📄 PDF Uploads: Upload & preview invoice files (e.g., PDF receipts).
- 📦 Storage: Store uploaded documents locally or on AWS S3 with signed URLs.
- 🔐 Access Control: Restrict download/view access based on user roles.
- 🧠 Audit Logs: Log PDF views/downloads for traceability.
- 🔍 Filters, Pagination, Search: Built-in support for all listings.
- 🔔 Polished UI: Confirmation modals, toasts, loading states, validations.
- 📈 Dashboard Ready: Designed to expand to analytics, charts, notifications.

---

## ⚙️ Tech Stack

| Layer       | Technology                                  |
|-------------|---------------------------------------------|
| Backend     | Django, Django REST Framework, Celery, Redis, PostgreSQL |
| Frontend    | React, Tailwind CSS, react-router-dom, Axios, react-dropzone, react-pdf |
| Task Queue  | Celery + Redis                              |
| Storage     | Local (dev) / AWS S3 (prod)                 |
| Auth        | Django Sessions / JWT (extensible)          |
| DevOps      | Docker, Docker Compose, Nginx               |
| Testing     | Django tests, Cypress, Jest (coming soon)   |

---

## 🏗️ Architecture Overview

Diagrams:
- [📊 Architecture Diagram](docs/diagrams/architecture.md)
- [📊 Architecture Diagram](docs/diagrams/ArchitectureDiagram.svg)
- [🖥️ UI Page Navigation Flow](docs/diagrams/ui-flow-diagram.md)
- [🧩 Backend Component Map](docs/diagrams/backend-component-map.md)
- [🧩 Frontend Component Map](docs/diagrams/frontend-component-map.md)
- [🌲 Component Tree View](docs/diagrams/component-tree.md)

---

## Centralise Common Models and Utilities
```
paystream/
│
├── core/                      # A new app for common models, mixins, and utilities
│   ├── __init__.py
│   ├── models.py              # Common models like TimeStampedModel, ActiveManager
│   ├── managers.py            # Common managers (e.g., ActiveManager)
│   ├── migrations/            # Migrations for core app
│   └── apps.py                # Core app configuration
│
├── clients/                   # Clients app
│   ├── __init__.py
│   ├── models.py
```

It is a good practice to **centralize common models and utilities** like `TimeStampedModel` and `ActiveManager` in a separate app or module, especially when they will be reused across multiple apps in your project. This helps maintain **modularity**, **reusability**, and **organization**. This organization helps avoid code duplication and makes your Django project more modular and scalable. By centralizing shared functionality in a `core` app, you ensure that any future changes to common models or managers only need to be made in one place, which greatly simplifies maintenance.

### **Why Centralize Common Models and Utilities?**

1. **Reusability**: You can easily reuse these models (or mixins) across any number of apps without duplicating the code.
2. **Separation of Concerns**: Keeping shared logic in a single place keeps your apps focused on their own domain logic, reducing clutter in individual apps.
3. **Easier Maintenance**: If you need to update or fix something in `TimeStampedModel` or `ActiveManager`, you only need to do it in one place, which reduces the risk of inconsistencies and bugs.
4. **Cleaner Code**: Instead of having `TimeStampedModel` and `ActiveManager` scattered across multiple apps, you can import them as needed, keeping your individual app files cleaner.

### **How to Structure It?**

You can create a **shared app** or module dedicated to common models, mixins, and utilities. This can be an app that holds the **base models** and any shared functionality, for example, an app called `core` or `common`.

Here’s how you could do it:

### **1. Create a `core` App for Shared Models**

#### **Folder Structure**

```plaintext
my_project/
│
├── core/                      # A new app for common models, mixins, and utilities
│   ├── __init__.py
│   ├── models.py              # Common models like TimeStampedModel, ActiveManager
│   ├── managers.py            # Common managers (e.g., ActiveManager)
│   ├── migrations/            # Migrations for core app
│   └── apps.py                # Core app configuration
│
├── clients/                   # Your existing clients app
│   ├── __init__.py
│   ├── models.py
│   └── ...
│
└── finance/                   # Your existing finance app
    ├── __init__.py
    ├── models.py
    └── ...
```

### **1. Move `TimeStampedModel` and `ActiveManager` to `core/models.py`**

Move the `TimeStampedModel` and `ActiveManager` to `core/models.py`. This way, any app can import them as needed.

#### **core/models.py**

```python
from django.db import models
from django.utils import timezone

class TimeStampedModel(models.Model):
    """Abstract base model that provides created and updated timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True  # This model will not create a database table

class ActiveManager(models.Manager):
    """Manager for active objects, excludes soft-deleted entries."""
    def active(self):
        return self.filter(deleted_at__isnull=True)

class SoftDeletableModel(models.Model):
    """Abstract base model that provides soft delete functionality."""
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
```

#### **core/managers.py**

If you have additional managers like `ActiveManager`, it's a good idea to keep them in a separate file for clarity.

```python
from django.db import models

class ActiveManager(models.Manager):
    """Manager to retrieve only active (non-deleted) objects."""
    def active(self):
        return self.filter(deleted_at__isnull=True)
```

### **3. Import and Use in Other Apps**

Now, in any app (e.g., `clients`, `finance`, etc.), you can import `TimeStampedModel` and `ActiveManager` from the `core` app.

For example, in your `clients/models.py`, you would do the following:

```python
from core.models import TimeStampedModel, ActiveManager  # Import from core

class Client(TimeStampedModel):
    name = models.CharField(max_length=255)
    # Other fields...
    
    objects = ActiveManager()  # Using ActiveManager
```

Similarly, in `finance/models.py`, you would import and use them as well.

```python
from core.models import TimeStampedModel, ActiveManager  # Import from core

class Invoice(TimeStampedModel):
    """Model for client invoices with detailed metadata."""
    # Define fields...
    
    objects = ActiveManager()  # Using ActiveManager
```

### **4. Benefits of This Approach**

1. **Single Source of Truth**: Both `TimeStampedModel` and `ActiveManager` are defined in one place (in `core`), so you don’t have to worry about redundancy and inconsistencies when using them across apps.
2. **Cleaner App Structure**: The logic for base models and managers is decoupled from business-specific logic in apps like `clients` or `finance`.
3. **Easy Maintenance**: When you need to update the base models or managers, you only need to update them in the `core` app, which ensures consistency across the entire project.
4. **Modular Architecture**: It follows a modular approach to organizing your project, making it easier to scale or add more shared functionality in the future (like shared signals, utilities, etc.).

### **5. Additional Organizational Suggestions**

* **`core/models.py`**: Put all abstract models and base models like `TimeStampedModel`, `SoftDeletableModel`, etc.
* **`core/managers.py`**: Put custom managers like `ActiveManager`, `DeletedManager`, etc.
* **`core/utils.py`**: Put utility functions that can be shared across multiple apps.
* **`core/signals.py`**: Put common signal handlers that can be used across apps (if needed).

---

## 📘 Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for setup instructions, style guide, and pull request process.

---

## 📜 License

This project is open-source and licensed under the MIT License.

---

## 🙌 Acknowledgements

- Inspired by real-world freelancer workflows
- Uses best practices for full-stack modular development
