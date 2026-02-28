from core.admin_mixins import AdminIconDecorator, BaseAdmin
from django.contrib.admin import display
from django.urls import reverse
from django.utils.html import format_html
from users.utils.helpers import user_is_verified_employee
from utilities.admin.admin_filters import HasAttachmentsFilter, changelist_filter

from helpdesk.forms import SupportForm
from helpdesk.models import SupportStatus, SupportTicket


@AdminIconDecorator.register_with_icon(SupportTicket)
class SupportAdmin(BaseAdmin):
    form = SupportForm

    list_display = (
        "ticket_number", "subject",
        "status_display", "email",
        "file_count", "created_at"
    )

    search_fields = ("ticket_number", "subject", "full_name", "email")
    list_per_page = 50
    autocomplete_fields = ["user"]
    actions = ['soft_delete', 'restore']

    base_fieldsets_config = [
        (None, {"fields": ("subject", "email", "message", "status", "resolved_at", "is_active")}),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    @display(description="Status")
    def status_display(self, obj):
        return SupportStatus[obj.status].label if obj.status else "-"

    @display(description="Attachments")
    def file_count(self, obj):
        count = obj.attachments.count()
        if not count:
            return "-"
        url = (
            reverse("admin:helpdesk_fileupload_changelist")
            + f"?object_id={obj.pk}"
        )
        return format_html('<a href="{}"><b>{}</b></a>', url, count)

    def get_list_filter(self, request):
        if user_is_verified_employee(request):
            return [
                changelist_filter("user"),
                changelist_filter("status"),
                changelist_filter("severity"),
                changelist_filter("emails_sent"),
                HasAttachmentsFilter,
            ]
