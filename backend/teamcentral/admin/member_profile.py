from core.admin_mixins import AdminIconDecorator, BaseAdmin
from django.contrib.admin import display
from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.urls import reverse
from django.utils.html import format_html
from users.utils.helpers import user_is_verified_employee
from utilities.admin.admin_filters import IsActiveFilter, changelist_filter

from teamcentral.forms import MemberProfileForm
from teamcentral.models import MemberProfile, MemberStatus

User = get_user_model()


@AdminIconDecorator.register_with_icon(MemberProfile)
class MemberProfileAdmin(BaseAdmin):
    form = MemberProfileForm

    list_display = (
        "member_code", "email",
        "first_name", "last_name",
        "employee_display", "status_display"
    )

    search_fields = ("member_code", "email", "first_name", "last_name")
    list_per_page = 50

    select_related_fields = ["status", "employee"]
    prefetch_related_fields = [
        Prefetch("status", queryset=MemberStatus.all_objects.filter(is_active=True)),
        Prefetch("employee", queryset=User.all_objects.filter(is_active=True)),
    ]

    actions = ["soft_delete", "restore"]
    autocomplete_fields = ["status", "employee", "address"]

    base_fieldsets_config = [
        (None, {
            "fields": (
                "email", "first_name", "last_name",
                "phone_number", "employee",
                "status", "address", "is_active"
            )
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    @display(description="Employee")
    def employee_display(self, obj):
        if obj.employee:
            return format_html(
                '<a href="{}">{}</a>',
                reverse("admin:users_employee_change", args=[obj.employee.pk]),
                obj.employee.employee_code,
            )
        return "-"

    @display(description="Status")
    def status_display(self, obj):
        if obj.status:
            return format_html(
                '<a href="{}">{}</a>',
                reverse("admin:teamcentral_memberstatus_change", args=[obj.status.pk]),
                obj.status.code,
            )
        return "-"

    def get_list_filter(self, request):
        base = [IsActiveFilter, changelist_filter("status")]
        if user_is_verified_employee(request):
            base.insert(0, changelist_filter(model=MemberProfile))
        return base

