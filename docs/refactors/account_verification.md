# User Account Verification Flow  #

Software Design & Requirements Document

**Feature:** Account / Email Verification

**Date:** 2025-12-24

---

## 1. Purpose

This document defines the **email verification workflow** implemented in the system, including:
- Functional requirements
- Design decisions
- Key logic points (with short code snippets)
- Explicit behavior across all user scenarios

The goal is to ensure the system is **secure, predictable, non–over-engineered**, and aligned with **real-world standards**.

---

## 2. Scope

This design covers:
- Signup email verification
- Token validation and consumption
- Behavior for authenticated, unauthenticated, and mismatched users

Out of scope:
- Session hijacking prevention beyond email ownership
- Browser/device binding
- Multi-factor authentication (handled separately)

---

## 3. Core Design Principle

### Email Ownership Is the Authority

> If a user can access the verification email and click the link, they are authorized to verify the account.

This follows the **industry-standard email verification model** used by major platforms.

---

## 4. Data Model Overview

### `SignUpRequest`
Represents a single verification attempt.

Key guarantees:
- One active token per user
- Token ownership is always resolvable
- Tokens are never hard-deleted (soft consumption)

Relevant fields:
- `user`
- `token`
- `expires_at`
- `deleted_at`

---

## 5. Token Lifecycle (High-Level)

1. User signs up
2. Token is generated and persisted
3. Token is emailed
4. Token is validated on access
5. Token is either:
   - Consumed (verified)
   - Rejected (invalid / expired / mismatched)

---

## 6. Validation Contract

The validation layer guarantees:

```python
TokenValidationResult(
    ok: bool,
    user: Optional[User],
    reason: Optional[str],
    signup_request: Optional[SignUpRequest],
)
````

**Important invariant**

```text
If a token ever existed, `user` is always known
(even if token is expired or consumed)
```

This enables deterministic ownership checks.

---
### **6.1 Token Ownership Preservation (Critical Implementation Detail)**

The validation layer **must resolve token ownership even after token consumption**.

To guarantee this, verification tokens are queried using a manager that includes soft-deleted records:

```python
req = SignUpRequest.all_objects.filter(token=token).first()
```

**Why this is required**

* Verification tokens are *soft-consumed* (`deleted_at` is set)
* Using the default manager would hide consumed tokens
* Hidden tokens break ownership detection and idempotent behavior

**Design invariant**

> If a verification token ever existed, its owning user **must always be resolvable**, regardless of token state (valid, expired, or consumed).

This invariant enables:

* Correct idempotent messaging for the original user
* Accurate rejection for mismatched logged-in users
* Stable behavior without view-layer branching explosions

---

## 7. Key Logic Points (Illustrative Snippets)

> ⚠️ These are **illustrative snippets**, not full implementations.

---

### 7.1 Token Validation (Service Layer)

```python
if req.deleted_at is not None:
    return TokenValidationResult(
        ok=False,
        reason="consumed",
        user=req.user,
        signup_request=req,
    )
```

Why:

* Enables idempotent behavior
* Preserves ownership after consumption

---

### 7.2 Ownership Check (View Layer)

```python
if request.user.is_authenticated and request.user.pk != result.user.pk:
    show_error("This verification link does not belong to your account")
```

Why:

* Prevents logged-in users from activating another account

---

### 7.3 Idempotent Success (Same User)

```python
if request.user.is_authenticated and request.user.pk == result.user.pk:
    show_info("This account has already been verified")
```

Why:

* Safe re-clicks
* No state mutation

---

### 7.4 Anonymous Verification

```python
if not request.user.is_authenticated and token_is_valid:
    consume_and_activate()
```

Why:

* Email possession is sufficient authorization
* Avoids login loops and UX friction

---

## 8. Functional Requirements

### FR-1: Token Ownership

* Every verification token must be associated with exactly one user.

### FR-2: Idempotency

* Reusing a verification link must never change state after first success.

### FR-3: Ownership Enforcement (Authenticated Users)

* A logged-in user cannot verify another user’s account.

### FR-4: Anonymous Verification

* Verification links must work without login.

### FR-5: Graceful Failure

* Invalid, expired, or reused tokens must produce clear messages.

---

## 9. Non-Functional Requirements

* **Security**: No cross-account activation
* **Reliability**: Deterministic outcomes for all cases
* **Maintainability**: No deep branching or fragile logic
* **User Experience**: Minimal friction

---

## 10. Explicit Behavior Matrix (Final Authority)

### Case A — Correct User, First Click

**State**

* Token valid
* User matches token

**Result**

* Account verified
* Token consumed
* Success message

---

### Case B — Same User Clicks Link Again

**State**

* Token consumed
* User matches token

**Result**

* No change
* Message:
  *“This account has already been verified.”*

---

### Case C — Different Logged-In User Clicks Link

**State**

* Token belongs to User A
* User B is logged in

**Result**

* Verification blocked
* Message:
  *“This verification link does not belong to your account.”*

---

### Case D — Anonymous User Clicks Valid Link

**State**

* Token valid
* No user logged in

**Result**

* Account verified
* Token consumed

**Rationale**

* Email possession is proof of ownership

---

### Case E — Anonymous User Clicks Consumed / Invalid Link

**State**

* Token consumed or invalid
* No user logged in

**Result**

* Message:
  *“This verification link is invalid or has already been used.”*

---

### Case F — Original User Logs In and Clicks Used Link

**State**

* Token consumed
* Correct user logged in

**Result**

* Message:
  *“This account has already been verified.”*

---

## 11. Design Trade-Offs (Explicit)

### What We Intentionally Did NOT Do

* Require login before verification
* Bind tokens to sessions or browsers
* Block anonymous verification
* Add excessive conditional logic

### Reason

These approaches increase complexity without improving real security and often break legitimate user flows.

---

## 12. Conclusion

The implemented verification flow:

* Matches real-world industry standards
* Handles all edge cases deterministically
* Avoids over-engineering
* Is secure, maintainable, and user-friendly

**Status:**
✅ Design complete
✅ Ready for production
✅ No further iteration required

---