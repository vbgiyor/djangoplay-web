# Account Verification Token Lifecycle (Canonical)

## 1. Creation (ONLY one entry point)

### **Owner**

`SignupTokenManagerService.create_for_user()`

### **When it is called**

* Manual signup
* Allauth signup (unverified users)
* Resend verification

### **Pre-conditions**

1. User exists
2. User is **not verified**
3. Rate-limit allows the action (`allow_flow`)

### **Algorithm**

```
create_for_user(user, flow):

  1. Enforce rate limits (EMAIL_FLOW_LIMITS)
     └── if blocked → return (None, "rate_limited")

  2. Check for existing ACTIVE token
     └── user + is_active=True + not deleted + not expired

     └── if exists → return (existing_token, "existing")

  3. Generate new token
     └── persist SignUpRequest row
     └── return (new_token, "ok")
```

### **Result**

* At most **ONE active token per user**
* Token creation is **idempotent**
* No model-level workflow rules

---

## 2. Storage (Data invariants only)

### **Model**

`SignUpRequest`

### **Meaning of fields**

| Field        | Meaning             |
| ------------ | ------------------- |
| `token`      | Proof of ownership  |
| `expires_at` | Time-bound validity |
| `is_active`  | Logical active flag |
| `deleted_at` | Consumption marker  |
| `user`       | Token owner         |

### **Invariant**

> A user may have **multiple historical tokens**,
> but **only one active, unexpired token** at any time.

This invariant is enforced by:

* `SignupTokenManagerService`
* NOT by the model enforcing “max 1 ever”

---

## 3. Distribution (Email)

### **Owner**

Mailer flows (Celery)

### **Rules**

* **Mailer NEVER creates tokens**
* **Mailer NEVER rotates tokens**
* **Mailer ONLY receives token reference**

### **Flow**

```
SignupFlowService
  └── create_for_user()
      └── returns signup_request

View / Service
  └── passes signup_request.id to Celery

Mailer
  └── builds verification URL from token
  └── sends email
```

### **Important**

If mail fails:

* Token remains valid
* User can resend
* No new token is created unless rotated

---

## 4. Resend Verification

### **Owner**

`resend_verification_for_email_task`
→ delegates to `SignupTokenManagerService.create_for_user`

### **Behavior**

* Rate-limited via `EMAIL_FLOW_LIMITS["resend_verification"]`
* Reuses existing active token
* Never raises validation errors
* Never creates duplicates

### **Outcome**

* Same token
* New email
* Controlled by config, not DB constraints

### ***Policy***
"""
Verification token lifecycle (IMPORTANT – do not change casually)

Email verification represents a *single, idempotent intent*:
    "Confirm that this email address belongs to this identity."

For an unverified user, there MUST be at most one active verification token
at any time.

Key principles enforced here:

1. Token reuse over regeneration
   - Resending a verification email is a *delivery retry*, not a new intent.
   - Creating a new token on every resend would invalidate previously sent
     emails and introduce multiple valid credentials unnecessarily.
   - Reusing the same active token guarantees deterministic UX and avoids
     "invalid link" scenarios caused by delayed or reordered emails.

2. Security
   - Minimizes the number of valid secrets in the system.
   - Reduces attack surface and simplifies revocation.
   - Exactly one active token exists per identity until verification or expiry.

3. Idempotency
   - Verification links are safe to click multiple times.
   - Multiple resend requests do not mutate identity state.
   - Token lifecycle is independent of email delivery attempts.

4. Separation of concerns
   - Rate limiting controls *email delivery frequency* (handled elsewhere).
   - Token lifecycle controls *verification intent* (handled here).
   - Mailer tasks must NOT create, revoke, or reason about token state.

A new token should be generated ONLY when:
   - No active, unexpired verification token exists, OR
   - The previous token has expired or been consumed.

Any change to this behavior must consider:
   - email delivery reliability
   - rate-limit semantics
   - security implications
   - user experience guarantees
"""

---

## 5. Validation (Pure, Stateless)

### **Owner**

`SignupTokenManagerService.validate_token()`

### **Rules**

Validation depends **only on token**, not session or login state.

### **Algorithm**

```
validate_token(token):

  1. Token format check
  2. Token exists?
  3. Token deleted? → consumed
  4. Token expired? → expired
  5. Resolve user + member
```

### **Return**

`TokenValidationResult`

* ok / invalid / expired / consumed
* token owner
* associated member (if any)

---

## 6. Consumption (Single irreversible step)

### **Owner**

`SignupTokenManagerService.consume_and_activate()`

### **When**

* User clicks verification link
* Token validated as OK

### **What happens**

```
consume_and_activate(token):

  1. Mark ALL signup requests for user as deleted
     └── deleted_at = now()

  2. Mark EmailAddress verified

  3. Activate user
     └── is_verified = True
     └── employment_status = ACTV

  4. Activate member (if exists)
```

### **Properties**

* Idempotent
* Safe to retry
* Old links become invalid automatically

---

## 7. Post-consumption state

| Scenario                  | Result                       |
| ------------------------- | ---------------------------- |
| Old link clicked          | “Already verified”           |
| Resend after verification | Blocked (already_verified)   |
| Login                     | Allowed                      |
| New signup                | Blocked (identity invariant) |

---

## 8. What controls WHAT (clear boundaries)

| Concern                | Owner                       |
| ---------------------- | --------------------------- |
| How many emails        | `EMAIL_FLOW_LIMITS`         |
| When resend allowed    | `allow_flow()`              |
| Token reuse / creation | `SignupTokenManagerService` |
| Data consistency       | Model invariants            |
| Email content          | Mailer                      |
| Verification logic     | Service                     |
| UI behavior            | Frontend views              |

---

## 9. Lifecycle in one sentence

> **A verification token is created once, reused until consumed or expired, distributed via email, validated statelessly, and permanently invalidated on consumption — with resend frequency controlled by config, not database constraints.**

---
