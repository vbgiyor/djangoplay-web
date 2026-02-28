import logging

from core.admin_mixins import AdminIconDecorator, BaseAdmin
from users.utils.helpers import user_is_verified_employee
from utilities.admin.admin_filters import IsActiveFilter, changelist_filter

from teamcentral.models import Department

logger = logging.getLogger(__name__)


@AdminIconDecorator.register_with_icon(Department)
class DepartmentAdmin(BaseAdmin):
    list_display = ('code', 'name', 'get_is_active')
    search_fields = ('code', 'name')
    list_per_page = 50
    select_related_fields = ['created_by', 'updated_by', 'deleted_by']
    actions = ['soft_delete', 'restore']

    base_fieldsets_config = [
        (None, {
            'fields': ('code', 'name', 'is_active')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_queryset(self, request):
        return super().get_queryset(request).only(
            'code', 'name', 'is_active', 'created_by', 'updated_by', 'deleted_by'
        )

    def get_list_filter(self, request):
        base_filters = [IsActiveFilter]
        if user_is_verified_employee(request):
            base_filters.insert(0, changelist_filter(model=Department))
        return base_filters
