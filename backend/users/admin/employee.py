import logging

from core.admin_mixins import AdminIconDecorator, BaseAdmin
from django.contrib.admin import display
from django.db.models import Prefetch, Q
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from mailer.engine.unsubscribe import UnsubscribeService
from teamcentral.models import Department, EmployeeType, EmploymentStatus, Role
from utilities.admin.admin_filters import IsActiveFilter, changelist_filter

from users.forms.employee import EmployeeForm
from users.models import Employee
from users.utils.helpers import user_is_verified_employee

logger = logging.getLogger(__name__)


@AdminIconDecorator.register_with_icon(Employee)
class EmployeeAdmin(BaseAdmin):
    form = EmployeeForm

    list_display = (
        "full_name", "email", "username", "employee_code",
        "department_display", "role_display",
        "employment_status_display", "employee_type_display",
        "manager_display", "hire_date", "is_active_employee_display"
    )

    search_fields = (
        "employee_code", "username", "email",
        "first_name", "last_name", "phone_number", "national_id"
    )

    list_per_page = 50

    select_related_fields = [
        "employment_status", "department", "role",
        "employee_type", "manager",
        "created_by", "updated_by", "deleted_by"
    ]

    prefetch_related_fields = [
        Prefetch("department", queryset=Department.all_objects.filter(is_active=True)),
        Prefetch("role", queryset=Role.all_objects.filter(is_active=True)),
        Prefetch("employment_status", queryset=EmploymentStatus.objects.filter(is_active=True)),
        Prefetch("employee_type", queryset=EmployeeType.all_objects.filter(is_active=True)),
    ]

    actions = ["soft_delete", "restore"]

    readonly_fields = (
        "employee_code", "address_display",
        "unsubscribed_at", "deleted_at", "deleted_by",
        "created_at", "created_by", "updated_at", "updated_by"
    )

    base_fieldsets_config = [
        (None, {
            "fields": (
                "first_name", "last_name", "username", "email",
                "sso_id", "sso_provider", "phone_number",
                "department", "role", "team",
                "employment_status", "employee_type",
                "manager", "address",
                "is_active", "is_verified"
            )
        }),
        (_("Details"), {
            "fields": (
                "job_title", "approval_limit", "avatar",
                "hire_date", "termination_date",
                "salary", "date_of_birth", "national_id",
                "emergency_contact_name", "emergency_contact_phone",
                "probation_end_date", "contract_end_date",
                "gender", "marital_status",
                "bank_details", "notes", "preferences"
            )
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if search_term:
            queryset = queryset.filter(
                Q(email__icontains=search_term) |
                Q(first_name__icontains=search_term) |
                Q(last_name__icontains=search_term)
            )
        return queryset, use_distinct

    def get_list_filter(self, request):
        base = [
            IsActiveFilter,
            changelist_filter("department"),
            changelist_filter("role"),
            changelist_filter("employment_status"),
            changelist_filter("employee_type"),
        ]
        if user_is_verified_employee(request):
            base.insert(0, changelist_filter(model=Employee))
        return base

    @display(description="Full Name")
    def full_name(self, obj):
        return obj.get_full_name

    @display(description="Department")
    def department_display(self, obj):
        if obj.department:
            return format_html(
                '<a href="{}">{}</a>',
                reverse("admin:teamcentral_department_change", args=[obj.department.pk]),
                obj.department
            )
        return "-"

    @display(description="Role")
    def role_display(self, obj):
        if obj.role:
            return format_html(
                '<a href="{}">{}</a>',
                reverse("admin:teamcentral_role_change", args=[obj.role.pk]),
                obj.role.code
            )
        return "-"

    @display(description="Employment Status")
    def employment_status_display(self, obj):
        if obj.employment_status:
            return format_html(
                '<a href="{}">{}</a>',
                reverse("admin:teamcentral_employmentstatus_change", args=[obj.employment_status.pk]),
                obj.employment_status.code
            )
        return "-"

    @display(description="Employee Type")
    def employee_type_display(self, obj):
        if obj.employee_type:
            return format_html(
                '<a href="{}">{}</a>',
                reverse("admin:teamcentral_employeetype_change", args=[obj.employee_type.pk]),
                obj.employee_type.code
            )
        return "-"

    @display(description="Manager")
    def manager_display(self, obj):
        if obj.manager:
            return format_html(
                '<a href="{}">{}</a>',
                reverse("admin:teamcentral_employee_change", args=[obj.manager.pk]),
                obj.manager.employee_code
            )
        return "-"

    @display(description="Is Active Employee", boolean=True)
    def is_active_employee_display(self, obj):
        return obj.is_active_employee

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if not change or "preferences" not in form.changed_data:
            return

        prefs = obj.preferences or {}
        if prefs and all(prefs.get(k) is True for k in prefs):
            UnsubscribeService.resubscribe_user(obj)
