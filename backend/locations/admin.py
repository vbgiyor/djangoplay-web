from django.contrib import admin, messages

from .models import City, Country, GlobalRegion, State

# --- Reusable Soft Delete and Restore Actions ---

def soft_delete_action(model_name):
    @admin.action(description=f"Mark selected {model_name.lower()}s as deleted")
    def action(modeladmin, request, queryset):
        updated = 0
        for obj in queryset:
            if hasattr(obj, 'deleted_at') and obj.deleted_at is None and callable(getattr(obj, 'soft_delete', None)):
                obj.soft_delete()
                updated += 1
        msg = f"{updated} {model_name}(s) marked as deleted." if updated else f"No {model_name.lower()}s were deleted."
        modeladmin.message_user(request, msg, messages.SUCCESS if updated else messages.INFO)

    action.__name__ = f"soft_delete_{model_name.lower()}"
    return action


def restore_action(model_name):
    @admin.action(description=f"Restore selected {model_name.lower()}s")
    def action(modeladmin, request, queryset):
        updated = 0
        for obj in queryset:
            if hasattr(obj, 'deleted_at') and obj.deleted_at is not None and callable(getattr(obj, 'restore', None)):
                obj.restore()
                updated += 1
        msg = f"{updated} {model_name}(s) restored." if updated else f"No {model_name.lower()}s were restored."
        modeladmin.message_user(request, msg, messages.SUCCESS if updated else messages.INFO)

    action.__name__ = f"restore_{model_name.lower()}"
    return action

# --- Admin Classes ---

@admin.register(GlobalRegion)
class GlobalRegionAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'global_region')
    list_filter = ('global_region',)
    search_fields = ('name', 'code')


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'country')
    list_filter = ('country',)
    search_fields = ('name', 'code', 'country__name')


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = (
        'address_line1', 'city', 'state', 'country', 'postal_code',
        'created_at', 'updated_at', 'deleted_at'
    )
    list_filter = ('country', 'state', 'city', 'deleted_at')
    search_fields = (
        'address_line1', 'address_line2', 'city', 'postal_code',
        'landmark', 'country__name', 'state__name'
    )
    raw_id_fields = ('created_by', 'updated_by')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    actions = [soft_delete_action("City"), restore_action("City")]

    fieldsets = (
        (None, {
            'fields': (
                'country', 'state', 'city', 'postal_code',
                'address_line1', 'address_line2', 'landmark'
            )
        }),
        ('Audit Info', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
