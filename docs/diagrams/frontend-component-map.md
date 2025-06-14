## 📁 Frontend Component Map for PayStream project

```
📁 src/
├── 📁 components/                   # Reusable UI components organized by domain
│   ├── 📁 clients/
│   │   ├── ClientList.jsx           # Displays list of clients with pagination & filters
│   │   ├── ClientForm.jsx           # Create/Edit client form with validation
│   │   ├── ClientDetailCard.jsx    # Shows detailed client info in card format
│   │   └── ClientDeleteModal.jsx   # Confirmation modal for deleting a client
│   │
│   ├── 📁 invoices/
│   │   ├── InvoiceList.jsx          # Invoice list with filtering and pagination
│   │   ├── InvoiceForm.jsx          # Invoice creation and edit form, with file upload
│   │   ├── InvoiceDetailCard.jsx   # Detailed invoice view card component
│   │   ├── InvoiceDeleteModal.jsx  # Confirmation modal for deleting invoice
│   │   ├── PDFUpload.jsx            # Component for uploading invoice PDFs (drag & drop)
│   │   └── PDFPreview.jsx           # Preview PDF invoices with zoom and page navigation
│   │
│   ├── 📁 audit/
│   │   └── AuditLogTable.jsx        # Displays audit logs in a table with filters
│   │
│   ├── 📁 auth/
│   │   ├── LoginForm.jsx            # Login form with JWT authentication
│   │   ├── RegisterForm.jsx         # User registration form
│   │   └── RequireRole.jsx          # Higher-order component (HOC) or wrapper to restrict access by user role
│   │
│   ├── 📁 layout/
│   │   ├── Navbar.jsx               # Navigation bar with links and auth status
│   │   └── Footer.jsx               # Footer component
│   │
│   ├── 📁 common/
│   │   ├── Pagination.jsx           # Generic pagination component
│   │   ├── SearchBar.jsx            # Search input with debounced filtering
│   │   ├── Toast.jsx                # Toast notifications for success/error messages
│   │   └── ConfirmModal.jsx         # Generic confirmation modal used across the app
│   │
│   ├── 📁 context/
│   │   └── UserContext.jsx          # React context provider for user auth state and info
│   │
│   └── AppWrapper.jsx               # Wraps routing and context providers for the app
│
├── 📁 pages/                       # Top-level pages for routes
│   ├── HomePage.jsx                # Dashboard or landing page after login
│   ├── ClientsPage.jsx             # Clients list and management page
│   ├── InvoicesPage.jsx            # Invoices list and management page
│   ├── AuditLogsPage.jsx           # Page to view audit logs
│   ├── LoginPage.jsx               # Login page rendering LoginForm
│   ├── RegisterPage.jsx            # Registration page rendering RegisterForm
│   └── NotFoundPage.jsx            # 404 page for unmatched routes
│
├── 📁 utils/                      # Utility functions and API helpers
│   ├── api.js                     # Axios instance pre-configured with base URL and auth interceptors
│   ├── auth.js                    # JWT token helpers: store, decode, refresh
│   ├── roles.js                   # User role checkers for authorization control
│   └── formatters.js              # Date, currency, and other formatting utilities
│
├── App.jsx                        # Main app component defining routes and layout
└── main.jsx                       # ReactDOM render, top-level entry point
```

---

### Key Features & Responsibilities

* **Clients Components:** CRUD UI for clients with clean forms, listing, and modals for delete confirmation.
* **Invoices Components:** Similar CRUD UI with additional file upload and PDF preview support.
* **Auth Components:** Login/register and role-based access control components.
* **Audit Components:** View audit trail logs of user actions.
* **Layout Components:** Navbar and footer, consistent app styling and navigation.
* **Common Components:** Reusable UI pieces like pagination, modals, search bar, and toast notifications.
* **Context:** Manages user session and auth state globally.
* **Utils:** API abstraction and helper functions for token handling and data formatting.
* **Pages:** Route targets that compose UI components into full pages.

---