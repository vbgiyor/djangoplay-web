from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone

from .models import User


class DeletedStatusFilter(SimpleListFilter):
    title = 'Deleted Status'
    parameter_name = 'deleted_status'

    def lookups(self, request, model_admin):
        return (
            ('deleted', 'Deleted'),
            ('not_deleted', 'Not Deleted'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'deleted':
            return queryset.filter(deleted_at__isnull=False)
        if self.value() == 'not_deleted':
            return queryset.filter(deleted_at__isnull=True)
        return queryset


class UserAdmin(UserAdmin):
    model = User
    list_display = (
        'username', 'id', 'employee_code', 'get_full_name', 'email', 'department', 'role',
        'approval_limit', 'phone_number', 'job_title', 'region', 'timezone', 'is_staff', 'is_active',
        'created_at', 'updated_at', 'deleted_at'
    )
    list_filter = ('is_active', 'is_staff', 'department', 'role', DeletedStatusFilter)
    search_fields = ('username', 'email', 'id', 'employee_code', 'first_name', 'last_name')
    ordering = ('id',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'region', 'job_title', 'avatar', 'timezone')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Employee Info', {'fields': ('id', 'employee_code', 'department', 'role', 'approval_limit', 'manager')}),
        ('Audit Info', {'fields': ('created_at', 'updated_at', 'created_by', 'updated_by', 'deleted_at')}),
    )

    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('username', 'email', 'password1', 'password2')}),
        ('Personal info', {'classes': ('wide',), 'fields': ('first_name', 'last_name', 'phone_number', 'region', 'job_title', 'avatar', 'timezone')}),
        ('Permissions', {'classes': ('wide',), 'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Employee Info', {'classes': ('wide',), 'fields': ('department', 'role', 'approval_limit', 'manager')}),
    )

    readonly_fields = ('id', 'employee_code', 'created_at', 'updated_at', 'created_by', 'updated_by', 'deleted_at')
    actions = ['soft_delete_users', 'restore_users']

    def get_queryset(self, request):
        return User.all_users.all()

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description='Soft delete selected users')
    def soft_delete_users(self, request, queryset):
        deleted = queryset.filter(deleted_at__isnull=True).update(deleted_at=timezone.now())
        self.message_user(request, f"{deleted} user(s) soft deleted successfully.", messages.SUCCESS)

    @admin.action(description='Restore selected users')
    def restore_users(self, request, queryset):
        restored = queryset.filter(deleted_at__isnull=False).update(deleted_at=None)
        self.message_user(request, f"{restored} user(s) restored successfully.", messages.SUCCESS)


admin.site.register(User, UserAdmin)
