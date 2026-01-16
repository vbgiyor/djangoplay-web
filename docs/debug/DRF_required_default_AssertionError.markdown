# DRF `required` + `default` AssertionError — Root Cause & Fix

## Context

While integrating **DRF serializers** with **drf-yasg** (Swagger/OpenAPI), the following error occurred when accessing `/swagger/`:

```
AssertionError: May not set both `required` and `default`
```

This is a **common DRF validation error** that surfaces when a serializer field is misconfigured with both:

* `required=True` (or implicitly required), and
* `default=...`

These two options are contradictory because:

* `required=True` means: “This field **must** be provided by the client.”
* `default=...` means: “If the client does not provide a value, **use this default**.”

DRF enforces mutual exclusivity.

---

## Root Cause

1. In our `InvoiceSerializer` and related serializers (`line_item.py`, `status.py`, etc.), several fields were defined like this:

```python
status = serializers.PrimaryKeyRelatedField(
    queryset=Status.objects.filter(is_active=True),
    required=False,  # but sometimes default was set too
    default=Status.objects.filter(is_default=True).first
)
```

2. DRF saw both `required=False` and `default` defined at field level.
3. Swagger (drf-yasg) attempted schema generation, iterated through serializer fields, and hit the **assertion check** inside `rest_framework/fields.py`.

---

## Why `extra_kwargs` Matters

Even after explicitly marking fields with `required=False`, the conflict persisted because:

* The **Meta class `extra_kwargs`** is the canonical way DRF resolves serializer field options when combined with defaults from the model.
* Without overriding in `extra_kwargs`, DRF still tried to apply model-level defaults **and** your serializer definitions, leading to conflict.

Example fix:

```python
class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = [...]
        extra_kwargs = {
            "status": {"required": False},
            "currency": {"required": False},
            "tax_exemption_status": {"required": False},
        }
```

This explicitly tells DRF:

* “Don't require these fields,”
* and prevents DRF from merging model defaults with serializer defaults.

---

## Step-by-Step Fix

1. **Scan for offenders** with `grep`:

```bash
# Look for explicit "required=" usage
grep -R --include="*.py" -n "required" invoices/serializers/

# Look for "default=" usage
grep -R --include="*.py" -n "default" invoices/serializers/

# Look for "initial=" (sometimes used in forms/serializers)
grep -R --include="*.py" -n "initial" invoices/serializers/

# Look for extra_kwargs in Meta (common culprit for DRF conflicts)
grep -R --include="*.py" -n "extra_kwargs" invoices/serializers/

# Look for overridden get_fields() (fields might be modified dynamically)
grep -R --include="*.py" -n "get_fields" invoices/serializers/

# Look for custom __init__ in serializers (fields might be altered there)
grep -R --include="*.py" -n "__init__" invoices/serializers/
```

2. **Remove field-level `default`** if also using `required`.
   Example — ❌ problematic:

   ```python
   status = serializers.PrimaryKeyRelatedField(
       queryset=Status.objects.all(),
       required=False,
       default=Status.objects.filter(is_default=True).first
   )
   ```

   ✅ fixed (move logic to `to_internal_value` or `create`):

   ```python
   status = serializers.PrimaryKeyRelatedField(
       queryset=Status.objects.all(),
       required=False
   )

   def to_internal_value(self, data):
       if not data.get("status"):
           data["status"] = Status.objects.filter(is_default=True).first()
       return super().to_internal_value(data)
   ```

3. **Use `extra_kwargs`** in `Meta` to override DRF's auto-generated constraints.

---

## How DRF Treats `required` vs `default`

* `required=True`: The field **must** appear in incoming data; omission triggers `ValidationError`.
* `default=value`: If missing from incoming data, DRF silently assigns the default **before validation**.
* They **cannot coexist**, because “must provide” contradicts “will auto-fill.”

---

## Takeaway

* Avoid setting both `required` and `default` at the same time.
* Use `extra_kwargs` for consistency with model defaults.
* Move complex default logic into `to_internal_value`, `create`, or `update`.
* Always scan serializer definitions when facing `AssertionError: May not set both required and default`.

---