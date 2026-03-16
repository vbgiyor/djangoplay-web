# Identity & Permissions

---

## Identity Flow (Login / Signup / SSO)

```
User Action
   │
   ▼
Frontend View
   │
   ▼
users.views
   │
   ▼
users.services.identity_*
   │
   ├─ Signup / Verification
   ├─ Password Reset
   ├─ SSO Onboarding
   │
   ▼
users.models (Employee, SignupRequest)
```

**Key Characteristics**

* Tokens are short-lived and purpose-specific
* Signup, verification, and reset flows are isolated
* Identity logic is never duplicated outside `users`

---

## Permission Evaluation Flow

```
Incoming Request
   │
   ▼
Authentication
   │
   ▼
policyengine
   ├─ Role evaluation
   ├─ Action permission
   ├─ Feature flags
   │
   ▼
Allow / Deny
```

**Key Characteristics**

* No app performs ad-hoc permission checks
* Permissions are centrally evaluated through `policyengine`
* Deny is the default outcome — fail-closed by design