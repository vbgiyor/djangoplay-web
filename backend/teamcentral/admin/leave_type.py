from core.admin_mixins import AdminIconDecorator, BaseAdmin
from users.utils.helpers import user_is_verified_employee
from utilities.admin.admin_filters import IsActiveFilter, changelist_filter

from teamcentral.forms import LeaveTypeForm
from teamcentral.models import LeaveType


@AdminIconDecorator.register_with_icon(LeaveType)
class LeaveTypeAdmin(BaseAdmin):
    form = LeaveTypeForm

    list_display = ("name", "code", "default_balance", "is_active")
    search_fields = ("name", "code")
    list_per_page = 50
    actions = ["soft_delete", "restore"]

    base_fieldsets_config = [
        (None, {"fields": ("name", "code", "default_balance", "is_active")}),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_list_filter(self, request):
        base = [IsActiveFilter]
        if user_is_verified_employee(request):
            base.insert(0, changelist_filter(model=LeaveType))
        return base
