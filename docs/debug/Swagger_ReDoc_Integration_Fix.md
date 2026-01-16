### ✅ **Swagger + ReDoc Custom Integration Fix Log – DjangoPlay**

> This document summarizes the diagnosis and resolution of Swagger/ReDoc integration issues using `drf-spectacular` in the DjangoPlay project.

---

## 🧩 Problem Summary

Swagger & ReDoc integration faced multiple challenges, including:

* Improper rendering of Swagger and ReDoc pages
* Swagger UI showing unwanted `cookieAuth` method
* Schema being publicly exposed or not loading
* 403 pages not redirecting correctly
* Auto-included documentation routes showing up in the schema

---

## 🔍 Root Causes & Fixes

### 1. **ReDoc JavaScript 404**

* **Issue:**
  ReDoc page failed to load due to `redoc.standalone.js` 404.

* **Root Cause:**
  referenced a missing static file instead of a CDN version.

* **Fix:**
  In `redoc.html`, replaced:

  ```html
  <script src="{% static 'js/redoc.standalone.js' %}"></script>
  ```

  with:

  ```html
  <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"></script>
  ```

---

### 2. **Relative schema path error in ReDoc**

* **Issue:**
  Schema was requested from the wrong path like:
  `/api/v1/redoc/api/v1/schema/`

* **Root Cause:**
  Relative path passed to `Redoc.init()` inside a nested route.

* **Fix:**
  Changed in `redoc.html`:

  ```js
  Redoc.init("/api/v1/schema/", {...}, ...)
  ```

---

### 3. **Swagger UI showing unwanted `cookieAuth`**

* **Issue:**
  Swagger's "Authorize" dialog showed:

  * `BasicAuth`
  * `BearerAuth`
  * **`cookieAuth` (unwanted)**

* **Root Cause:**
  `SessionAuthentication` was detected implicitly and exposed as `cookieAuth`.

* **Fix:**

  1. Explicitly defined only desired security schemes in `SPECTACULAR_SETTINGS`:

     ```python
     "COMPONENTS": {
         "securitySchemes": {
             "BasicAuth": {
                 "type": "http",
                 "scheme": "basic",
             },
             "BearerAuth": {
                 "type": "http",
                 "scheme": "bearer",
                 "bearerFormat": "JWT",
             },
         }
     },
     "SECURITY": [
         {"BasicAuth": []},
         {"BearerAuth": []},
     ],
     ```
  2. Ensured `SessionAuthentication` was used only where necessary and not at schema level.

---

### 4. **403 Forbidden Doesn't Redirect to Login**

* **Issue:**
  After hitting a restricted route, the 403 template showed the login form, but even after logging in, users were stuck on the same page.

* **Root Cause:**
  The `SwaggerView` had `authentication_classes = []` which disabled session detection after login.

* **Fix:**
  Restored authentication classes in `CustomSpectacularSwaggerView`:

  ```python
  authentication_classes = [BasicAuthentication, JWTAuthentication, SessionAuthentication]
  ```

* **Also Implemented:**
  Graceful error handling via custom 403 template (`403_login.html`) in:

  * `CustomSpectacularAPIView`
  * `CustomSpectacularSwaggerView`
  * `CustomSpectacularRedocView` (excluded from auth entirely)

---

### 5. **Swagger/Redoc/Schema Showing in OpenAPI Output**

* **Issue:**
  The documentation-related routes (`/swagger/`, `/redoc/`, `/schema/`) were appearing in the generated schema.

* **Root Cause:**
  `drf-spectacular` auto-discovers all views, including internal ones.

* **Fix:**
  Created a preprocessing hook in `apidocs/hooks.py`:

  ```python
  def exclude_docs_views(endpoints):
      return [
          (path, path_regex, method, callback)
          for path, path_regex, method, callback in endpoints
          if "apidocs.views" not in callback.__module__
      ]
  ```

  And added to `SPECTACULAR_SETTINGS`:

  ```python
  "PREPROCESSING_HOOKS": [
      "drf_spectacular.hooks.preprocess_exclude_path_format",
      "apidocs.hooks.exclude_docs_views",
  ],
  ```

---

## 🧱 Final Architecture Overview

### ⚙️ `SPECTACULAR_SETTINGS` (simplified)

```python
SPECTACULAR_SETTINGS = {
    "TITLE": "DjangoPlay APIs",
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAuthenticated"],
    "SWAGGER_UI_TEMPLATE": "drf_spectacular/swagger.html",
    "SWAGGER_UI_SETTINGS": {
        "url": "/api/v1/schema/",
        "persistAuthorization": True,
        ...
    },
    "COMPONENTS": {
        "securitySchemes": {
            "BasicAuth": {"type": "http", "scheme": "basic"},
            "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
        }
    },
    "SECURITY": [
        {"BasicAuth": []},
        {"BearerAuth": []},
    ],
    "PREPROCESSING_HOOKS": [
        "drf_spectacular.hooks.preprocess_exclude_path_format",
        "apidocs.hooks.exclude_docs_views",
    ],
}
```

---

## 🎨 UX Enhancements

* Swagger UI footer includes helpful links via injected JS
* Clean 403 template with inline login form
* Custom Redoc styling with full-screen layout
* `/swagger`, `/redoc`, `/schema` hidden from schema consumers

---

## ✅ Outcome

| Feature                              | Status     |
| ------------------------------------ | ---------- |
| ReDoc renders without 404s           | ✅ Resolved |
| Swagger UI loads with no cookieAuth  | ✅ Resolved |
| Internal routes excluded from schema | ✅ Resolved |
| 403 Login page functional            | ✅ Resolved |
| JWT + Basic Auth support only        | ✅ Resolved |

---

## 📁 Project Files of Interest

| File                                 | Purpose                                 |
| ------------------------------------ | --------------------------------------- |
| `views/swagger.py`, `views/redoc.py` | Custom Swagger & ReDoc views            |
| `templates/drf_spectacular/*.html`   | Custom UI templates for docs & 403 page |
| `hooks.py`                           | Schema filtering logic                  |
| `drf_spectacular.py`                 | Global schema settings                  |
| `urls.py` (project-level + apidocs/) | Routing for docs + schema endpoints     |

---
