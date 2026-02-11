from core.admin_mixins import AdminIconDecorator, BaseAdmin
from django.contrib.admin import display
from django.urls import reverse
from django.utils.html import format_html
from users.utils.helpers import user_is_verified_employee
from utilities.admin.admin_filters import FileCategoryFilter, TicketTypeFilter, changelist_filter

from helpdesk.models import BugReport, FileUpload, SupportTicket


@AdminIconDecorator.register_with_icon(FileUpload)
class FileUploadAdmin(BaseAdmin):
    list_display = (
        "original_name_link",
        "related_object_link",
        "size_display",
        "uploaded_at",
        "ticket_type",
        "created_by"
    )

    readonly_fields = (
        "original_name_link",
        "size",
        "uploaded_at",
        "created_by",
        "related_object_link"
    )

    ordering = ("-uploaded_at",)
    actions = ['soft_delete', 'restore']
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @display(description="File")
    def original_name_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            obj.file.url,
            obj.original_name
        )

    @display(description="Size")
    def size_display(self, obj):
        return f"{obj.size / 1024:.1f} KB" if obj.size else "-"

    @display(description="Related Ticket")
    def related_object_link(self, obj):
        if not obj.content_object:
            return "-"

        target = obj.content_object

        # SupportTicket
        if isinstance(target, SupportTicket):
            url = reverse(
                "admin:helpdesk_supportticket_change",
                args=[target.pk],
            )
            return format_html(
                '<a href="{}"><b>{}</b></a>',
                url,
                target.ticket_number,
            )

        # BugReport
        if isinstance(target, BugReport):
            url = reverse(
                "admin:helpdesk_bugreport_change",
                args=[target.pk],
            )
            return format_html(
                '<a href="{}"><b>{}</b></a>',
                url,
                target.bug_number,
            )

        # Fallback (future-safe)
        return str(target)

    @display(description="Ticket Type")
    def ticket_type(self, obj):
        if not obj.content_object:
            return "-"

        if isinstance(obj.content_object, SupportTicket):
            return "Support"

        if isinstance(obj.content_object, BugReport):
            return "Bug"

        return "Other"

    def get_list_filter(self, request):
        base = [
            FileCategoryFilter,
            TicketTypeFilter,
            changelist_filter("mime_type"),
            # changelist_filter("content_type")
        ]
        if user_is_verified_employee(request):
            base.insert(0, changelist_filter(model=FileUpload))
        return base


