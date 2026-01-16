from apidocs.models.apirequestlog import APIRequestLog
from django.contrib import admin


@admin.register(APIRequestLog)
class APIRequestLogAdmin(admin.ModelAdmin):
    list_display = ('method', 'path', 'response_status', 'user', 'timestamp', 'is_public_api', 'auto_detected')
    list_filter = ('is_public_api', 'method', 'response_status', 'timestamp')
    search_fields = ('path', 'user__username', 'user__email', 'client_ip')
    readonly_fields = ('timestamp', 'client_ip', 'user_agent', 'auto_detected')
    list_editable = ('is_public_api',)  # ← Manual override

    def auto_detected(self, obj):
        # Visual cue: was it auto-set?
        return "Yes" if obj.pk else "—"
    auto_detected.short_description = "Auto?"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
