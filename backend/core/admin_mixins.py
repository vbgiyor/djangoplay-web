import json
import logging
from datetime import date, datetime
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.helpers import AdminForm
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

# ---------- Constants ----------
AUDIT_FIELDSET = (_('Metadata'), {
    'fields': ('created_by', 'updated_by', 'created_at', 'updated_at')
})
DEFAULT_SNAPSHOT_TTL = 5 * 60  # seconds

# ---------- Small utilities ----------
def display_value(value):
    """
    Convert DB values into a readable display form for history diffs.
    Kept intentionally minimal and safe.
    """
    if value in (None, "", [], {}, ()):
        return "(none)"

    # Model instances / FKs: prefer str()
    try:
        if hasattr(value, "__str__"):
            return str(value)
    except Exception:
        pass

    if isinstance(value, (date, datetime)):
        try:
            return value.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(value)

    if isinstance(value, bool):
        return "Yes" if value else "No"

    return str(value)


# ---------- Mixins ----------
class SoftDeleteMixin:

    """Provide easy soft-delete / restore admin actions (calls model soft_delete/restore)."""

    soft_delete_msg = "{} item(s) soft deleted successfully."
    restore_msg = "{} item(s) restored successfully."

    @admin.action(description="Soft delete selected items")
    def soft_delete(self, request, queryset):
        updated = 0
        for item in queryset.filter(deleted_at__isnull=True):
            item.soft_delete(user=request.user)
            updated += 1
        self.message_user(request, self.soft_delete_msg.format(updated), messages.SUCCESS)

    @admin.action(description="Restore selected items")
    def restore(self, request, queryset):
        updated = 0
        for item in queryset.filter(deleted_at__isnull=False):
            item.restore(user=request.user)
            updated += 1
        self.message_user(request, self.restore_msg.format(updated), messages.SUCCESS)


class ReadonlyPermissionsMixin:

    """Simple permission toggles you can override on an admin."""

    add_permission = True
    change_permission = True
    delete_permission = False

    def has_add_permission(self, request):
        return self.add_permission

    def has_change_permission(self, request, obj=None):
        return self.change_permission

    def has_delete_permission(self, request, obj=None):
        return self.delete_permission

    def has_view_permission(self, request, obj=None):
        return True


class OptimizedQuerysetMixin:

    """
    Small mixin to centralize select_related/prefetch_related hints on admin classes.
    Set `select_related_fields` and `prefetch_related_fields` on the admin class.
    """

    select_related_fields = []
    prefetch_related_fields = []

    def get_queryset(self, request):
        qs = getattr(self.model, '_base_manager', self.model.objects).all()
        if self.select_related_fields:
            qs = qs.select_related(*self.select_related_fields)
        if self.prefetch_related_fields:
            qs = qs.prefetch_related(*self.prefetch_related_fields)
        return qs


class AuditLogMixin:

    """Log admin create/update/soft_delete calls to the project logger."""

    def log_action(self, request, obj, action, details=None):
        logger_name = f"{obj._meta.app_label}.admin"
        logger_local = logging.getLogger(logger_name)
        msg = f"User {request.user} performed {action} on {obj._meta.model_name} {obj}"
        if details:
            msg += f": {details}"
        logger_local.info(msg)

    def save_model(self, request, obj, form, change):
        action = "update" if change else "create"
        self.log_action(request, obj, action)
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        self.log_action(request, obj, "soft_delete")
        super().delete_model(request, obj)


class AuditVisibilityMixin:

    """
    Who can see the audit fieldset. Superusers always see it.
    You can extend to support role-based rules.
    """

    def user_can_see_audit(self, request):
        if request.user.is_superuser:
            return True
        role = getattr(request.user, 'role', None)
        role_code = getattr(role, 'code', None)
        # Example: hide audit from SSO role
        restricted_roles = {'SSO'}
        return role_code not in restricted_roles

    def get_audit_fields(self, obj=None):
        fields = ['created_by', 'updated_by', 'created_at', 'updated_at']
        if obj and getattr(obj, 'deleted_at', None):
            fields += ['deleted_at', 'deleted_by']
        return fields


class FieldsetMixin(AuditVisibilityMixin):

    """
    Compose fieldsets from base configuration plus conditional ones.
    Admin classes may set:
      - base_fieldsets_config: list of tuples like (title, {'fields': (...)})
      - conditional_fieldsets: dict mapping keys -> fieldset tuples
      - get_fieldset_conditions(request, obj) -> list of keys to include
    """

    base_fieldsets_config = []
    conditional_fieldsets = {}

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_injected_fieldsets(self, request, obj=None):
        fieldsets = list(self.base_fieldsets_config)
        for condition in self.get_fieldset_conditions(request, obj):
            if condition in self.conditional_fieldsets:
                fieldsets.append(self.conditional_fieldsets[condition])
        return fieldsets

    def get_fieldsets(self, request, obj=None):
        # Compose final fieldsets, adding metadata when allowed
        fieldsets = self.get_injected_fieldsets(request, obj)
        # ensure no duplicate metadata entries
        fieldsets = [fs for fs in fieldsets if fs[0] != _('Metadata')]
        if self.user_can_see_audit(request):
            fieldsets.append((_('Metadata'), {'fields': self.get_audit_fields(obj)}))
        return fieldsets


class HistoryMixin:

    """
    Provide human-friendly diffs built from django-simple-history records.
    The backfill script resolved missing '+' rows in your DB — therefore this
    implementation is intentionally simpler and robust.

    Behavior:
      - Only superusers see history (caller checks in change_view)
      - Creation ('+') rows are ignored in display (they represent object creation)
      - Update ('~') rows are compared to their prev_record; if prev_record is None (oldest "~"),
        we treat it as baseline and by default do NOT show (unless a snapshot exists in cache)
      - De-duplication of identical diff entries is performed
      - Optional: if a per-request snapshot exists in cache, we will synthesize a first-edit diff.
    """

    def _history_cache_key(self, obj, request):
        return f"admin_history_snap:{obj._meta.app_label}.{obj._meta.model_name}:{obj.pk}:{request.user.pk}"

    def _record_to_display_map(self, obj, rec):
        """Return dict field_name -> display string for a historical record object."""
        mapping = {}
        for field in obj._meta.fields:
            try:
                val = getattr(rec, field.name, None)
            except Exception:
                val = None
            mapping[field.name] = display_value(val)
        return mapping

    # def _build_diffs_from_maps(self, obj, old_map, new_map, hist_date=None, hist_user=None):
    #     diffs = []
    #     audit_names = {'id', 'slug', 'created_at', 'updated_at', 'created_by', 'updated_by', 'deleted_at', 'deleted_by', 'is_active'}
    #     for field in obj._meta.fields:
    #         if field.name in audit_names:
    #             continue
    #         old_disp = old_map.get(field.name, "(none)")
    #         new_disp = new_map.get(field.name, "(none)")
    #         if old_disp != new_disp:
    #             diffs.append({
    #                 "action_time": hist_date,
    #                 "user": hist_user or "System",
    #                 "field": field.verbose_name.title(),
    #                 "old_value": old_disp,
    #                 "new_value": new_disp,
    #             })
    #     return diffs

    def _build_diffs_from_maps(self, obj, old_map, new_map, hist_date=None, hist_user=None):
        audit_names = {'id', 'slug', 'created_at', 'updated_at', 'created_by', 'updated_by', 'deleted_at', 'deleted_by', 'is_active'}
        sensitive_names = {'password'}

        return [
            {
                "action_time": hist_date,
                "user": hist_user or "System",
                "field": field.verbose_name.title(),
                "old_value": old_map.get(field.name, "(none)"),
                "new_value": new_map.get(field.name, "(none)")
            }
            for field in obj._meta.fields
            if field.name not in audit_names and field.name not in sensitive_names and old_map.get(field.name, "(none)") != new_map.get(field.name, "(none)")
        ]


    def get_history_user(self, request, obj):
        """Return structured history for display to superusers (or [] for others)."""
        # In case if history to be limited only for superusers
        # if not request.user.is_superuser:. For everyone, as below
        if obj is None:
            return []

        try:
            historical_records = list(obj.history.all().order_by('-history_date'))
            if not historical_records:
                return []

            history = []
            # load optional snapshot payload (set by CustomAdminFormMixin on GET)
            snapshot_payload = None
            try:
                raw = cache.get(self._history_cache_key(obj, request))
                if raw:
                    snapshot_payload = json.loads(raw)
                    try:
                        cache.delete(self._history_cache_key(obj, request))
                    except Exception:
                        pass
            except Exception:
                snapshot_payload = None

            # If snapshot exists build a display map: field -> display
            snapshot_map = None
            snapshot_ts = None
            if snapshot_payload:
                snap_data = snapshot_payload.get("data", {})
                snapshot_map = {}
                for field in obj._meta.fields:
                    item = snap_data.get(field.name)
                    if isinstance(item, dict):
                        snapshot_map[field.name] = item.get("_display") or "(none)"
                    else:
                        snapshot_map[field.name] = display_value(item)
                try:
                    snapshot_ts = parse_datetime(snapshot_payload.get("meta", {}).get("ts")) if snapshot_payload.get("meta", {}).get("ts") else None
                except Exception:
                    snapshot_ts = None

            # iterate history (newest -> oldest)
            for i, current in enumerate(historical_records):
                prev = historical_records[i + 1] if i + 1 < len(historical_records) else None

                # skip creation rows from display
                if current.history_type == "+":
                    continue

                # standard update with a previous record: compare prev -> current
                if current.history_type == "~" and prev is not None:
                    prev_map = self._record_to_display_map(obj, prev)
                    curr_map = self._record_to_display_map(obj, current)
                    history.extend(self._build_diffs_from_maps(obj, prev_map, curr_map, hist_date=current.history_date, hist_user=(getattr(current, 'history_user', None) or "System")))
                    continue

                # oldest "~" with no prev: candidate for synthetic diff if we have a snapshot
                if current.history_type == "~" and prev is None:
                    if snapshot_map:
                        # if snapshot timestamp is present, only synthesize if this record is after snapshot_ts
                        if snapshot_ts is None or (getattr(current, 'history_date', None) and current.history_date > snapshot_ts):
                            curr_map = self._record_to_display_map(obj, current)
                            history.extend(self._build_diffs_from_maps(obj, snapshot_map, curr_map, hist_date=current.history_date, hist_user=(getattr(current, 'history_user', None) or "System")))
                    # otherwise: do not show baseline change (creation) — backfill should have created '+' rows
                    continue

                # deletion
                if current.history_type == "-":
                    history.append({
                        "action_time": current.history_date,
                        "user": (getattr(current, 'history_user', None) or "System"),
                        "field": "(deleted)",
                        "old_value": display_value(obj),
                        "new_value": "(deleted)",
                    })

            # dedupe by (field, action_time, old, new)
            seen = set()
            deduped = []
            for entry in history:
                # normalize action_time for hashability
                act = entry['action_time']
                act_key = act.isoformat() if hasattr(act, "isoformat") else act
                key = (entry['field'], act_key, entry['old_value'], entry['new_value'])
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(entry)

            # newest-first sort
            return sorted(deduped, key=lambda x: x["action_time"], reverse=True)
        except Exception as exc:
            logger.warning("History failed: %s", exc)
            return []


    def log_change(self, request, obj, message):
        # override admin default to avoid double logging — we handle history display elsewhere
        return


class InitialHistoryMixin:

    """
    Optional: attach to model admin class before save to create an initial '+' row
    if you want to automatically create initial history on object creation.
    !IMPORTANT: Use this mixin at model levels, not app level ONLY if you want to safeguard
    old legacy data added before simple history creation.
    Example Usage:
        class CustomCountry(InitialHistoryMixin, TimeStampedModel, AuditFieldsModel)
    """

    def _create_initial_history_record(self, instance):
        """
        Create '+' history record on instance if desired.
        NOTE: prefer DB backfill for large legacy datasets.
        """
        if hasattr(instance, "history") and not instance.history.filter(history_type='+').exists():
            try:
                instance.history.create(
                    history_type='+',
                    history_date=getattr(instance, "created_at", timezone.now()),
                    **{f.name: getattr(instance, f.name) for f in instance._meta.fields}
                )
            except Exception as exc:
                logger.exception("Failed to create initial history: %s", exc)


class SoftDeleteFormMixin:

    """
    When editing a soft-deleted instance, disable fields in the form.
    Avoid exposing deleted_by / deleted_at fields on normal edit forms.
    """

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and getattr(obj, 'deleted_at', None):
            for name in list(form.base_fields):
                form.base_fields[name].disabled = True
        # hide soft-delete internals when editing active objects
        if not obj or not getattr(obj, 'deleted_at', None):
            for hide in ('deleted_at', 'deleted_by'):
                if hide in form.base_fields:
                    del form.base_fields[hide]
        return form


class AdminIconDecorator:

    """
    Register admin with an icon attribute (used by your admin UI).
    Usage:
      @AdminIconDecorator.register_with_icon(MyModel)
      class MyModelAdmin(admin.ModelAdmin):
          ...
    """

    @staticmethod
    def register_with_icon(model_class):
        def decorator(admin_class):
            model_key = f"{model_class._meta.app_label}.{model_class.__name__}"
            try:
                from paystream.static.design.icons.admin_metadata import MODEL_ICON_MAP
                admin_class.icon = MODEL_ICON_MAP.get(model_key, "fas fa-database")
            except Exception:
                admin_class.icon = "fas fa-database"
            from paystream.custom_site.admin_site import admin_site
            admin_site.register(model_class, admin_class)
            return admin_class
        return decorator

class CustomAdminFormMixin:

    """
    Provide custom change/add form templates and snapshot storing on GET to help
    synthesize first-edit diffs when needed.
    """

    change_form_template = 'admin/changelist_edit.html'
    add_form_template = 'admin/changelist_add.html'

    def get_parent_url(self, request):
        return reverse(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist')

    def _get_admin_form(self, request, obj=None):
        form_class = self.get_form(request, obj)
        form_instance = form_class(
            data=request.POST if request.method == 'POST' else None,
            files=request.FILES if request.method == 'POST' else None,
            instance=obj
        )
        return AdminForm(
            form_instance,
            list(self.get_fieldsets(request, obj)),
            self.get_prepopulated_fields(request, obj),
            self.get_readonly_fields(request, obj),
            model_admin=self
        )

    def _resolve_audit_fields(self, obj=None):
        """
        Helper to compute audit field names that both:
        - come from get_audit_fields()
        - actually exist on the model
        """
        base = []
        if hasattr(self, "get_audit_fields"):
            base = self.get_audit_fields(obj) or []

        model_field_names = {f.name for f in self.model._meta.fields}
        return [f for f in base if f in model_field_names]


    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context.update({
            'parent_url': self.get_parent_url(request),
            'opts': self.model._meta,
            'adminform': self._get_admin_form(request),
            'add': True,
            'audit_fields': self.get_audit_fields(),
            'user_can_see_audit': self.user_can_see_audit(request),
        })
        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        Build a lightweight snapshot on GET and store in cache for a short TTL.
        The HistoryMixin can consume this snapshot to synthesize a first-edit diff.
        """
        clean_object_id = object_id.replace('_2F', '/') if '_2F' in object_id else object_id

        # fetch object (allow fallback)
        obj = self.get_object(request, clean_object_id)
        if not obj:
            from django.shortcuts import get_object_or_404
            obj = get_object_or_404(self.model, pk=clean_object_id)

        # store a simple snapshot on GET for the current user
        if request.method == 'GET' and request.user.is_authenticated:
            AUDIT_FIELDS = {'id', 'slug', 'created_at', 'updated_at', 'created_by', 'updated_by', 'deleted_at', 'deleted_by', 'is_active'}
            snapshot = {}
            for field in obj._meta.fields:
                if field.name in AUDIT_FIELDS:
                    continue
                try:
                    val = getattr(obj, field.name)
                except Exception:
                    val = None
                try:
                    if getattr(field, 'remote_field', None) and val is not None:
                        snapshot[field.name] = {"_display": force_str(val), "_pk": getattr(val, "pk", None)}
                    else:
                        snapshot[field.name] = {"_display": force_str(val) if val is not None else None, "_pk": None}
                except Exception:
                    snapshot[field.name] = {"_display": None, "_pk": None}

            payload = {"meta": {"ts": obj.updated_at.isoformat()}, "data": snapshot}
            try:
                cache.set(f"admin_history_snap:{obj._meta.app_label}.{obj._meta.model_name}:{obj.pk}:{request.user.pk}", json.dumps(payload), timeout=DEFAULT_SNAPSHOT_TTL)
            except Exception:
                logger.debug("Unable to set history snapshot in cache (non-fatal)")

        # history = self.get_history_user(request, obj) if request.user.is_superuser else []
        history = self.get_history_user(request, obj)

        extra_context = extra_context or {}
        extra_context.update({
            'parent_url': self.get_parent_url(request),
            'object': obj,
            'opts': self.model._meta,
            'has_delete_permission': self.has_delete_permission(request, obj),
            'delete_url': (
                reverse(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_delete',
                        args=[obj.pk.replace('/', '_2F') if isinstance(obj.pk, str) and '/' in obj.pk else obj.pk])
                if obj else ''
            ),
            'adminform': self._get_admin_form(request, obj),
            'add': False,
            'audit_fields': self.get_audit_fields(obj),
            'user_can_see_audit': self.user_can_see_audit(request),
            'history': history,
        })

        return super().change_view(request, clean_object_id, form_url, extra_context=extra_context)


class BaseAdmin( FieldsetMixin, CustomAdminFormMixin, HistoryMixin, SoftDeleteMixin, OptimizedQuerysetMixin, admin.ModelAdmin,):

    """
    Basic admin with:
      - read-only audit fields
      - optional simple _old_values tracking for other code paths
      - automatic inclusion of CustomAdminFormMixin (admin-level) via inheritance
      - default custom change list template
    """

    # Default changelist template for all admins (can be overridden per-admin)
    change_list_template = "admin/custom_changelist.html"

    list_display = ('id',)
    list_display_links = ("id",)
    ordering = ('-id',)

    def get_list_display(self, request):
        audit_fields = {'created_at', 'created_by', 'deleted_at', 'deleted_by', 'updated_at', 'updated_by'}
        base = super().get_list_display(request)
        return ('id',) + tuple(f for f in base if f not in audit_fields)

    def get_readonly_fields(self, request, obj=None):
        model_fields = [f.name for f in self.model._meta.fields]
        readonly = ['created_at', 'updated_at', 'created_by', 'updated_by']
        if obj and getattr(obj, 'deleted_at', None):
            readonly += ['deleted_at', 'deleted_by']
        return [f for f in readonly if f in model_fields]

    def get_fieldsets(self, request, obj=None):
        # delegate to FieldsetMixin-compatible method if present; else fallback to default
        if hasattr(self, 'get_injected_fieldsets'):
            fieldsets = self.get_injected_fieldsets(request, obj)
            fieldsets = [fs for fs in fieldsets if fs[0] != _('Metadata')]
            if self.user_can_see_audit(request):
                fieldsets.append((_('Metadata'), {'fields': self.get_audit_fields(obj)}))
            return fieldsets
        return super().get_fieldsets(request, obj)

    def save_model(self, request, obj, form, change):
        """
        Keep a minimal _old_values map on the instance for other admin logic.
        Non-invasive and safe.
        """
        # 1) snapshot old values
        if change:
            base_qs = getattr(self.model, "all_objects", self.model._base_manager)
            try:
                old_obj = base_qs.get(pk=obj.pk)
                obj._old_values = {
                    field: getattr(old_obj, field) for field in form.changed_data
                }
            except self.model.DoesNotExist:
                obj._old_values = {}
        else:
            obj._old_values = {}

        # 2) set audit fields if they exist
        if request.user.is_authenticated:
            # Only touch these if the model actually has them
            if hasattr(obj, "created_by") and hasattr(obj, "updated_by"):
                if not change or not getattr(obj, "created_by_id", None):
                    # new object, or created_by still empty
                    obj.created_by = request.user
                obj.updated_by = request.user

        # 3) let Django do the actual save
        super().save_model(request, obj, form, change)



    def get_is_active(self, obj):
        return getattr(obj, 'deleted_at', None) is None
    get_is_active.boolean = True
    get_is_active.short_description = "Active"


    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.setdefault('show_pagination_top', True)
        extra_context.setdefault('show_total_count', True)
        extra_context.setdefault('show_save_button_top', True)
        return super().changelist_view(request, extra_context=extra_context)

    def render_change_form(self, request, context, *args, **kwargs):
        context.setdefault('show_save_button_top', True)
        return super().render_change_form(request, context, *args, **kwargs)


class AdminURLMixin:
    def get_admin_url(self):
        ct = ContentType.objects.get_for_model(self)
        path = reverse(
            f"admin:{ct.app_label}_{ct.model}_change",
            args=[self.pk],
        )
        protocol = (
            "https"
            if getattr(settings, "SECURE_SSL_REDIRECT", False)
            else "http"
        )

        parsed = urlparse(settings.SITE_URL)
        base = parsed.netloc or parsed.path

        return f"{protocol}://{base}{path}"
