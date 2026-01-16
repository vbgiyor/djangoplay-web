# Employee or Member Address Management

**Status:** ✅ Frozen
**Last Updated:** 2026-01-11
**Scope:** `users.Address` model, admin UI, and activation logic

---

## 1. Purpose

The `Address` model stores **versioned address records** for a user (Employee / Member).

The system enforces a strict real-world rule:

> **At most one active address per user at any time**, while allowing unlimited historical (inactive) addresses.

This implementation is intentionally **simple, explicit, and non-over-engineered**.

---

## 2. Core Business Rules (Invariant)

At all times:

* A user can have **zero or one active address**
* A user can have **any number of inactive addresses**
* Active address is controlled explicitly via `is_active`
* Historical data is preserved (never overwritten)

This is enforced at:

* **Database level** (partial unique constraint)
* **Admin save logic** (transactional deactivation)

---

## 3. Address Model (`users.models.Address`)

### 3.1 Model Definition

```python
class Address(TimeStampedModel, AuditFieldsModel):
    """
    Stores versioned address records.
    Exactly ONE active address per owner is allowed.
    """
```

### 3.2 Ownership

```python
owner = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.PROTECT,
    related_name="addresses",
    help_text="Employee or Member owning this address",
)
```

* Each address belongs to exactly **one user**
* Ownership is immutable once created (read-only in admin edit)

---

### 3.3 Address Fields

```python
address = models.TextField(help_text="Full address text")
address_type = models.CharField(
    choices=[CURRENT, PERMANENT],
    help_text="Informational address type",
)
country, state, city, postal_code, emergency_contact
```

* `address_type` is **informational**
* Activation is **not tied** to address type

---

### 3.4 Activation Flag

```python
is_active = models.BooleanField(default=True)
```

* Explicit control over which address is active
* Admins may activate or deactivate addresses manually

---

### 3.5 Database Constraint (Hard Guarantee)

```python
constraints = [
    models.UniqueConstraint(
        fields=["owner"],
        condition=Q(is_active=True),
        name="one_active_address_per_owner",
    )
]
```

This guarantees:

* The database **cannot** contain two active addresses for the same user
* Any violation raises an `IntegrityError`

---

## 4. Admin UI (`AddressAdmin`)

### 4.1 List View

```python
list_display = (
    "owner",
    "address",
    "address_type",
    "is_active",
)
```

* Clearly shows which address is active
* Multiple rows per user are expected (history)

---

### 4.2 Search

```python
search_fields = (
    "owner__email",
    "address",
    "city",
)
```

Admins can locate addresses by:

* User email
* Address text
* City

---

## 5. Admin Form Behavior

### 5.1 ADD Form

**Purpose:** Create a new address for a user

Behavior:

* Shows **searchable Email field** (Select2)
* Hides read-only email display
* `is_active` is **forced to True**
* Any existing active address is automatically deactivated

---

### 5.2 EDIT Form

**Purpose:** Modify an existing address

Behavior:

* Shows **read-only Email**
* Owner cannot be changed
* `is_active` is editable
* Admin explicitly controls activation

---

## 6. Address Activation Rules (Frozen Logic)

These rules are enforced **only in `AddressAdmin.save_model()`**.

### 6.1 Rules (Authoritative)

```text
ADD:
- A newly created address is always set as active.
- Any existing active address for the same owner is automatically
  deactivated BEFORE the new address is saved.

EDIT:
- If is_active=True:
    - This address is promoted to be the owner's sole active address.
    - Any other active address for the same owner is deactivated
      BEFORE saving to satisfy the database constraint.
- If is_active=False:
    - The address is simply updated.
    - No other addresses are affected.

Invariant:
- At all times, an owner can have at most ONE active address.
- Zero or more inactive addresses are allowed.
```

---

### 6.2 Why Deactivation Happens **Before** Save

Because of the database constraint:

```sql
one_active_address_per_owner
```

We must ensure:

* No two `is_active=True` rows exist **at save time**
* Hence: deactivate → then save

This ordering is **intentional and required**.

---

## 7. Address Admin Save Implementation (Final)

```python
def save_model(self, request, obj, form, change):
    owner = obj.owner if change else form.cleaned_data.get("user")
    if not owner:
        raise ValidationError("Address must have an owner.")

    with transaction.atomic():

        # ADD
        if not change:
            obj.owner = owner
            obj.is_active = True

            Address.all_objects.filter(
                owner=owner,
                is_active=True,
            ).update(is_active=False)

            super().save_model(request, obj, form, change)
            return

        # EDIT
        if obj.is_active:
            Address.all_objects.filter(
                owner=owner,
                is_active=True,
            ).exclude(pk=obj.pk).update(is_active=False)

        super().save_model(request, obj, form, change)
```

This code is **final and correct**.

---

## 8. AddressForm (`AddressForm`)

### 8.1 Purpose

* Separate **user selection** (ADD) from **user display** (EDIT)
* Prevent accidental owner changes
* Keep UI simple and predictable

---

### 8.2 Key Behavior

```python
ADD:
- Show searchable Email field (Select2)
- Email is required

EDIT:
- Hide user search field
- Show Email as read-only
```

---

## 9. Design Principles Followed

* ✅ DRY
* ✅ Explicit over implicit
* ✅ Database-enforced invariants
* ✅ No signals
* ✅ No hidden magic
* ✅ Admin controls behavior, model enforces truth

---
