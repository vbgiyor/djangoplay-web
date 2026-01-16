# Django Admin Notes

## Practical, Real‑World Django Admin Fix

### Problem Statement

When editing an Address (`/console/users/address/<id>/change/`), the admin UI must clearly show **who owns the address**:

* Employee (internal user)
* Member (external/social user)

Constraints:

* Ownership is **reverse‑FK**, not a direct field on Address
* No schema changes
* No migrations
* No template changes
* Must work with a **generic admin template**
* Must align with Django best practices and DRY principles

---

## What This Gave You Immediately

**Admin Address list page** now shows:

* Which employee owns the address
* Which member (if any) references it

**Edit Address page** now shows:

* Employee name + email *or*
* Member name + email
* Never both

All of this was achieved:

* Without model changes
* Without migrations
* Without template hacks
* Without brittle CSS or JS

This is exactly how Django Admin is designed to be extended.

---

## Why This Is the Right Solution for Your Case

### ✔ Aligns with Django philosophy

* Uses reverse relations
* Avoids redundant foreign keys

### ✔ DRY

* One Address table
* No duplicated ownership columns

### ✔ Real‑world precedent

This pattern is extremely common in:

* CRM systems
* ERP back offices
* Enterprise admin dashboards
* Legacy Django applications

---

## Key Principle: Why This Works

You already had ownership information:

```
Employee.address → FK(Address) → address.employees.all()
Member.address   → FK(Address) → address.members.all()
```

Ownership **exists**, but it is not a form field.

Django Admin supports:

* Read‑only contextual fields
* Custom form fields
* Dynamic fieldsets

The goal is **to surface derived metadata**, not persist it.

---

## The Correct Django Mental Model (Critical)

### Admin pages behave differently

| Page      | Controlled by  |
| --------- | -------------- |
| List page | `list_display` |
| Edit page | `fieldsets`    |

> ❗ **Readonly ≠ visible** unless the field is included in a fieldset

---

## Important Discovery: BaseAdmin vs ModelAdmin

You are **not** using Django’s default `ModelAdmin`.

You are inheriting from **`BaseAdmin`**.

### What this changes fundamentally

* `get_fields()` is **ignored**
* `fieldsets` are **authoritative**
* Fields come from `base_fieldsets_config`
* Extra fields are injected later
* Your template renders **whatever adminform gives it**

This explains *all* confusing behavior seen earlier.

---

## Why Early Attempts Failed

### ❌ Using `get_fields()`

Ignored because `BaseAdmin` builds fieldsets itself.

### ❌ Using `readonly_fields` only

Readonly fields are **not rendered** unless placed in a fieldset.

### ❌ Using `HiddenInput`

Hides widgets **only**, not labels.

> ⚠️ Key rule
> Hiding a widget does NOT hide the label
> unless the template explicitly checks `field.is_hidden`.

Your template does not.

### ❌ Removing fields from the form (`pop()`)

Caused crashes:

```
KeyError: Key 'member_name' not found in AddressForm
```

Because:

* Admin controls layout
* Form must not change structure

---

## Non‑Negotiable Django Admin Rules (Lock These In)

1. **Admin controls field existence**
2. **Forms control values only**
3. **Templates blindly render adminform**
4. **Fieldsets are validated against the ModelForm**
5. **If a field appears in a fieldset, it MUST exist in the form**

---

## The Only Correct Solution (Given Your Constraints)

### Step 1: Form defines real, read‑only fields

Why:

* Fieldsets validate against form fields
* Admin display methods are NOT enough

Form responsibility:

* Declare fields
* Populate `.initial`
* Never remove fields

---

### Step 2: Base fieldsets stay model‑only (DRY)

```python
base_fieldsets_config = [
    (None, {
        "fields": (
            "address_type",
            "address",
            "address_type",
            "city",
            "state",
            "country",
            "postal_code",
            "emergency_contact",
            "is_active",
        )
    }),
]
```

Why:

* Keeps base config reusable
* No owner logic leakage

---

### Step 3: Inject owner fields dynamically via `get_fieldsets()`

This is the **correct extension point** in your architecture.

```python
def get_fieldsets(self, request, obj=None):
    fieldsets = super().get_fieldsets(request, obj)

    if not obj:
        return fieldsets

    employee = obj.employees.first()
    member = obj.members.first()

    owner_fields = []

    if employee:
        owner_fields = ("employee_name", "employee_email")
    elif member:
        owner_fields = ("member_name", "member_email")

    if owner_fields:
        return [
            (None, {"fields": owner_fields}),
            *fieldsets,
        ]

    return fieldsets
```

---

## Why This Finally Fixed Everything

| Problem                       | Why it disappeared                  |
| ----------------------------- | ----------------------------------- |
| Labels still showing          | Fields no longer exist in fieldsets |
| Hidden inputs rendered        | Fields never reach template         |
| Admin ignoring `get_fields()` | Correct hook used                   |
| Template untouched            | ✔                                   |
| Form untouched                | ✔                                   |
| DRY preserved                 | ✔                                   |

---

## Final Mental Model (Memorize This)

* **List page** → `list_display`
* **Edit page** → `fieldsets`
* **Readonly** → visible only if in fieldsets
* **Form fields** → must exist for fieldsets
* **Visibility** → admin responsibility
* **Values** → form responsibility

---

## If You Add a New Derived Field in the Future

Checklist:

1. Add field to the **ModelForm** (disabled=True)
2. Populate `.initial` only
3. Do NOT pop fields
4. Do NOT hide widgets
5. Inject field via `get_fieldsets()`
6. Never touch templates

---

## Final Takeaway

This was not trial‑and‑error.
This was discovering the **true control flow** of a customized Django Admin.

Once you understand:

> *Fieldsets are authoritative in your architecture*

Everything becomes predictable, debuggable, and scalable.

This is how large Django admin systems are actually built.

---

# Django Admin Rules Cheat Sheet (Architecture-Agnostic, Enterprise-Grade)

This cheat sheet applies to **any Django admin refactor**, not just the Address case.
It assumes you may be using:

* Custom BaseAdmin classes
* Generic admin templates
* Strict fieldset-driven rendering

---

## 1. Mental Model: Who Controls What

| Layer                      | Owns                                | Must NOT Do                        |
| -------------------------- | ----------------------------------- | ---------------------------------- |
| **Model**                  | Data, constraints, relations        | UI decisions, presentation logic   |
| **ModelForm**              | Validation, initial values, widgets | Layout, field existence decisions  |
| **ModelAdmin / BaseAdmin** | Field existence, order, visibility  | Data validation, value computation |
| **Template**               | Rendering only                      | Business logic, field decisions    |

Golden rule:

> **Structure belongs to Admin. Values belong to Form. Rendering belongs to Template.**

---

## 2. Field Visibility vs Field Existence (CRITICAL)

* **Existence** = whether a field is part of the adminform at all
* **Visibility** = whether the widget is visible

| Action                      | Result                              |
| --------------------------- | ----------------------------------- |
| Remove field from fieldsets | Field + label + widget gone ✅       |
| HiddenInput widget          | Widget hidden ❌ label still renders |
| disabled=True               | Read-only ❌ label still renders     |
| CSS hide                    | Fragile ❌ anti-DRY                  |

> If you don’t want to see a label, the field must **not exist** in the fieldset.

---

## 3. Fieldsets Are Authoritative (Non‑negotiable)

If your admin:

* uses `base_fieldsets_config`
* overrides `get_fieldsets()`
* renders from `adminform`

Then:

* `get_fields()` is ignored
* Django validates fieldsets strictly

Rule:

> **If a field appears in a fieldset, it must exist in the ModelForm.**

---

## 4. readonly_fields: What They Do (and Don’t)

✔ What readonly_fields do:

* Make fields non-editable
* Allow admin display methods to be rendered

❌ What they do NOT do:

* Add fields automatically to forms
* Bypass fieldset validation
* Hide labels

Readonly fields must still:

* Exist in fieldsets
* Exist in the form (directly or indirectly)

---

## 5. Admin Display Methods vs Form Fields

| Use Case                            | Correct Tool                    |
| ----------------------------------- | ------------------------------- |
| Show value in **list page**         | `list_display` + @admin.display |
| Show derived value **outside form** | messages / custom view          |
| Show derived value **inside form**  | **Form field (read-only)**      |

Key rule:

> **Anything inside a form must be a form field.**

---

## 6. Never Do This in Admin Forms

❌ `self.fields.pop()` in ModelForm
❌ Dynamically removing fields in `__init__`
❌ Relying on widget hiding for visibility
❌ Injecting HTML via messages for form data

Why:

* Admin already decided the structure
* You desync admin + form → crashes

---

## 7. Correct Way to Add Contextual, Read‑Only Data

Checklist:

1. Add field to ModelForm (disabled=True)
2. Populate via `__init__`
3. Control **existence** via Admin fieldsets
4. Never remove fields in the form

Admin decides *whether* the field exists.
Form decides *what value* it shows.

---

## 8. BaseAdmin‑Specific Rules (Important)

If inheriting from BaseAdmin:

* `base_fieldsets_config` is the source of truth
* `get_fields()` is ignored
* Only `get_fieldsets()` can change structure

Extension pattern:

* Base config → model-backed fields only
* Dynamic injection → context-specific fields

---

## 9. Debugging Django Admin (Systematic Approach)

When something doesn’t render:

1️⃣ Is the field in a fieldset?
2️⃣ Does the ModelForm define it?
3️⃣ Is admin expecting it?
4️⃣ Is the template blindly rendering?

If labels show unexpectedly → field exists.
If KeyError happens → form and admin disagree.

---

## 10. Final Golden Rules (Lock These In)

* Admin controls **structure**
* Form controls **values**
* Templates should stay dumb
* Fieldsets beat everything
* Visibility ≠ existence

If you remember only one thing:

> **If a field must appear in an admin form, it must exist in BOTH the fieldset and the form.**

---