import logging

from core.admin_mixins import AdminIconDecorator, BaseAdmin
from users.utils.helpers import user_is_verified_employee
from utilities.admin.admin_filters import *

from industries.models.industry import Industry

from .forms.industries import IndustryForm

logger = logging.getLogger('industries.admin')


@AdminIconDecorator.register_with_icon(Industry)
class IndustryAdmin(BaseAdmin):

    """Admin configuration for the Industry model."""

    form = IndustryForm
    list_display = ('code', 'description', 'level', 'sector', 'parent', 'is_active')
    search_fields = ['code', 'description']
    list_per_page = 50
    select_related_fields = ['parent', 'created_by', 'updated_by', 'deleted_by']
    prefetch_related_fields = ['children']
    autocomplete_fields = ['parent']
    actions = ['soft_delete', 'restore']

    base_fieldsets_config = [
        (None, {
            'fields': ('code', 'description', 'level', 'sector', 'parent')
        }),
    ]

    def get_list_filter(self, request):
        base = [changelist_filter("code"), changelist_filter("description"), changelist_filter("level"), changelist_filter("sector"), changelist_filter("parent"), IsActiveFilter ]
        if user_is_verified_employee(request):
            base.insert(0, changelist_filter(model=Industry))
        return base

