import logging

from core.admin_mixins import AdminIconDecorator, BaseAdmin
from django.contrib.admin import display
from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _
from utilities.admin.admin_filters import IsActiveFilter, changelist_filter

from users.forms import PasswordResetRequestForm
from users.models import Employee
from users.models.password_reset_request import PasswordResetRequest
from users.utils.helpers import user_is_verified_employee

logger = logging.getLogger(__name__)

@AdminIconDecorator.register_with_icon(PasswordResetRequest)
class PasswordResetRequestAdmin(BaseAdmin):
    form = PasswordResetRequestForm
    list_display = ('username', 'token_display', 'expires_at', 'used', 'is_active')
    list_filter = ()
    search_fields = ('user__email',)
    list_per_page = 50
    select_related_fields = ['user', 'created_by', 'updated_by', 'deleted_by']
    prefetch_related_fields = [
        Prefetch('user', queryset=Employee.all_objects.filter(is_active=True)),
    ]
    ordering = ('-created_at',)

    base_fieldsets_config = [
        (None, {
            'fields': ('user', 'expires_at', 'used', 'token')
        }),
    ]

    def get_readonly_fields(self, request, obj=None):
        # Always show expires_at as calculated value (read-only)
        return ('expires_at', 'token',) + tuple(super().get_readonly_fields(request, obj))

    def get_fieldsets(self, request, obj=None):
        # Let BaseAdmin inject audit fieldset first
        fieldsets = super().get_fieldsets(request, obj)

        if obj is None:
            # On ADD form → hide some fields
            new_fieldsets = []
            for title, opts in fieldsets:
                fields = list(opts.get('fields', []))
                if 'expires_at' in fields:
                    fields.remove('expires_at')
                if 'is_active' in fields:
                    fields.remove('is_active')
                if 'used' in fields:
                    fields.remove('used')
                if 'token' in fields:
                    fields.remove('token')
                new_fieldsets.append((title, {**opts, 'fields': fields}))
            return new_fieldsets

        # On EDIT: remove is_active but KEEP metadata
        new_fieldsets = []
        for title, opts in fieldsets:
            fields = list(opts.get('fields', []))
            if 'is_active' in fields:
                fields.remove('is_active')
            new_fieldsets.append((title, {**opts, 'fields': fields}))

        return new_fieldsets

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if 'user__search' in request.GET:
            queryset = queryset.filter(user__email__icontains=search_term)
        return queryset, use_distinct

    def get_queryset(self, request):
        return super().get_queryset(request).only(
            'user__email', 'expires_at', 'used', 'is_active', 'created_by', 'updated_by', 'deleted_by'
        )

    @display(description="User")
    def username(self, obj):
        return obj.user.get_full_name

    @display(description="Token")
    def token_display(self, obj):
        return obj.token

    @display(description="Expires At")
    def expires_at(self, obj):
        if not obj or not obj.expires_at:
            return "-"
        return obj.expires_at.strftime("%Y-%m-%d %H:%M:%S")


    def get_list_filter(self, request):
        base_filters = [
            # changelist_filter("user"),
            ('used'),
            IsActiveFilter,
        ]
        if user_is_verified_employee(request):
            base_filters.insert(0, changelist_filter('user'))
        return base_filters

