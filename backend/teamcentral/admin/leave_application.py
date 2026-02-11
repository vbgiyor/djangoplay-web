from core.admin_mixins import AdminIconDecorator, BaseAdmin
from django.contrib.admin import display
from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.urls import reverse
from django.utils.html import format_html
from users.utils.helpers import user_is_verified_employee
from utilities.admin.admin_filters import IsActiveFilter, changelist_filter

from teamcentral.forms import LeaveApplicationForm
from teamcentral.models import LeaveApplication, LeaveType

User = get_user_model()

@AdminIconDecorator.register_with_icon(LeaveApplication)
class LeaveApplicationAdmin(BaseAdmin):
    form = LeaveApplicationForm

    list_display = (
        "employee_display", "leave_type_display",
        "start_date", "end_date", "status", "approver", "is_active"
    )

    search_fields = ("employee__employee_code", "leave_type__name", "reason")
    list_per_page = 50
    ordering = ("-start_date",)

    select_related_fields = ["employee", "leave_type", "approver"]
    prefetch_related_fields = [
        Prefetch("employee", queryset=User.all_objects.filter(is_active=True)),
        Prefetch("leave_type", queryset=LeaveType.all_objects.filter(is_active=True)),
    ]

    actions = ["soft_delete", "restore"]
    autocomplete_fields = ["employee", "leave_type", "approver"]

    base_fieldsets_config = [
        (None, {
            "fields": (
                "employee", "leave_type", "start_date",
                "end_date", "hours", "reason",
                "status", "approver", "is_active"
            )
        }),
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

    def get_list_filter(self, request):
        base = [IsActiveFilter,
                changelist_filter("employee"),
                changelist_filter("leave_type"),
                changelist_filter("approver")]
        if user_is_verified_employee(request):
            base.insert(0, changelist_filter(model=LeaveApplication))
        return base
