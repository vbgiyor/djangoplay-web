from core.admin_mixins import AdminIconDecorator, BaseAdmin
from django.contrib.admin import display
from django.utils.translation import gettext_lazy as _
from policyengine.commons.base import get_user_role

from audit.constants import AUDIT_ADMIN_ROLES
from audit.models.audit_event import AuditEvent


@AdminIconDecorator.register_with_icon(AuditEvent)
class AuditEventAdmin(BaseAdmin):

    # ------------------------------------------------------------------
    # LIST VIEW
    # ------------------------------------------------------------------
    list_display = (
        "occurred_at",
        "action",
        "actor_display",
        "target_display",
        "client_ip",
        "is_system_event",
    )

    list_filter = (
        "action",
        "actor_type",
        "target_type",
        "is_system_event",
    )

    search_fields = (
        "actor_label",
        "target_label",
        "request_id",
    )

    ordering = ("-occurred_at",)
    list_per_page = 50
    date_hierarchy = "occurred_at"

    # ------------------------------------------------------------------
    # DETAIL VIEW (READ-ONLY)
    # ------------------------------------------------------------------
    readonly_fields = (
        "occurred_at",
        "action",
        "actor_type",
        "actor_id",
        "actor_label",
        "target_type",
        "target_id",
        "target_label",
        "client_ip",
        "request_id",
        "user_agent",
        "is_system_event",
        "metadata",
    )

    fieldsets = (
        (_("Event"), {
            "fields": (
                "occurred_at",
                "action",
                "is_system_event",
            )
        }),
        (_("Actor"), {
            "fields": (
                "actor_type",
                "actor_id",
                "actor_label",
            )
        }),
        (_("Target"), {
            "fields": (
                "target_type",
                "target_id",
                "target_label",
            )
        }),
        (_("Request Context"), {
            "fields": (
                "client_ip",
                "request_id",
                "user_agent",
            )
        }),
        (_("Metadata"), {
            "fields": ("metadata",),
        }),
    )

    # ------------------------------------------------------------------
    # HARD PERMISSION RULES
    # ------------------------------------------------------------------
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # ------------------------------------------------------------------
    # ROLE-BASED VISIBILITY
    # ------------------------------------------------------------------
    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        role = get_user_role(request.user)
        return role in AUDIT_ADMIN_ROLES

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        role = get_user_role(request.user)
        if role not in AUDIT_ADMIN_ROLES:
            return qs.none()

        return qs


    # ------------------------------------------------------------------
    # DISPLAY HELPERS
    # ------------------------------------------------------------------
    @display(description="Actor")
    def actor_display(self, obj):
        if obj.actor_label:
            return f"{obj.actor_label} ({obj.actor_type})"
        return "-"

    @display(description="Target")
    def target_display(self, obj):
        if obj.target_label:
            return f"{obj.target_label} ({obj.target_type})"
        return "-"
