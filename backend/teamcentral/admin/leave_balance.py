from core.admin_mixins import AdminIconDecorator, BaseAdmin
from django.contrib.admin import display
from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.urls import reverse
from django.utils.html import format_html
from utilities.admin.admin_filters import IsActiveFilter, changelist_filter

from teamcentral.forms import LeaveBalanceForm
from teamcentral.models import LeaveBalance, LeaveType

User = get_user_model()


@AdminIconDecorator.register_with_icon(LeaveBalance)
class LeaveBalanceAdmin(BaseAdmin):
    form = LeaveBalanceForm

    list_display = ("employee_display", "leave_type_display", "balance", "year", "is_active")
    search_fields = ("employee__employee_code", "leave_type__name")
    list_per_page = 50
    ordering = ("-year",)

    select_related_fields = ["employee", "leave_type"]
    prefetch_related_fields = [
        Prefetch("employee", queryset=User.all_objects.filter(is_active=True)),
        Prefetch("leave_type", queryset=LeaveType.all_objects.filter(is_active=True)),
    ]

    actions = ["soft_delete", "restore"]
    autocomplete_fields = ["employee", "leave_type"]

    base_fieldsets_config = [
        (None, {"fields": ("employee", "leave_type", "balance", "year", "used", "reset_date", "is_active")}),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_list_filter(self, request):
        return [
            IsActiveFilter,
            changelist_filter("employee"),
            changelist_filter("leave_type"),
        ]

    @display(description="Employee")
    def employee_display(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse("admin:users_employee_change", args=[obj.employee.pk]),
            obj.employee.employee_code,
        )

    @display(description="Leave Type")
    def leave_type_display(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse("admin:users_leavetype_change", args=[obj.leave_type.pk]),
            obj.leave_type.name,
        )
