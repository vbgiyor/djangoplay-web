from core.admin_mixins import AdminIconDecorator, BaseAdmin
from django.contrib.admin import display
from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.urls import reverse
from django.utils.html import format_html
from users.utils.helpers import user_is_verified_employee
from utilities.admin.admin_filters import IsActiveFilter, changelist_filter

from teamcentral.forms import TeamForm
from teamcentral.models import Department, Team

User = get_user_model()


@AdminIconDecorator.register_with_icon(Team)
class TeamAdmin(BaseAdmin):
    form = TeamForm

    list_display = ("name", "department_display", "leader_display", "is_active")
    search_fields = ("name", "description")
    list_per_page = 50
    ordering = ("-id",)

    select_related_fields = ["department", "leader", "created_by", "updated_by", "deleted_by"]
    prefetch_related_fields = [
        Prefetch("department", queryset=Department.all_objects.filter(is_active=True)),
        Prefetch("leader", queryset=User.all_objects.filter(is_active=True)),
    ]

    actions = ["soft_delete", "restore"]
    autocomplete_fields = ["department", "leader"]

    base_fieldsets_config = [
        (None, {"fields": ("name", "department", "leader", "description", "is_active")}),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    @display(description="Department")
    def department_display(self, obj):
        if obj.department:
            return format_html(
                '<a href="{}">{}</a>',
                reverse("admin:teamcentral_department_change", args=[obj.department.pk]),
                obj.department.code,
            )
        return "-"

    @display(description="Leader")
    def leader_display(self, obj):
        if obj.leader:
            return format_html(
                '<a href="{}">{}</a>',
                reverse("admin:users_employee_change", args=[obj.leader.pk]),
                obj.leader.employee_code,
            )
        return "-"

    def get_list_filter(self, request):
        base = [
                IsActiveFilter,
                changelist_filter("department"),
                changelist_filter("leader"),
                ]
        if user_is_verified_employee(request):
            base.insert(0, changelist_filter(model=Team))
        return base

