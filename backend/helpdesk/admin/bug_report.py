from core.admin_mixins import AdminIconDecorator, BaseAdmin
from django.contrib.admin import display
from django.urls import reverse
from django.utils.html import format_html
from users.utils.helpers import user_is_verified_employee
from utilities.admin.admin_filters import HasAttachmentsFilter, changelist_filter

from helpdesk.forms import BugReportForm
from helpdesk.models import BugReport, BugStatus, Severity


@AdminIconDecorator.register_with_icon(BugReport)
class BugReportAdmin(BaseAdmin):

    """
    Thin admin.
    No business logic.
    No visibility logic.
    """

    form = BugReportForm

    list_display = (
        "bug_number",
        "summary",
        "status_display",
        "severity_display",
        "reporter_email",
        "attachment_count",
        "created_at",
    )

    search_fields = (
        "bug_number",
        "summary",
        "steps_to_reproduce",
        "reporter__email",
    )

    autocomplete_fields = ["reporter"]
    actions = ['soft_delete', 'restore']
    list_per_page = 50

    # IMPORTANT: readonly only, NOT part of form fields
    readonly_fields = ("attachments_display",)

    base_fieldsets_config = [
        (
            "Details",
            {
                "fields": (
                    "summary",
                    "steps_to_reproduce",
                    "expected_result",
                    "actual_result",
                    "status",
                    "severity",
                    "external_issue_url",
                    "is_active",
                )
            },
        ),
    ]

    def get_injected_fieldsets(self, request, obj=None):
        """
        Remove empty optional fields entirely (label + wrapper)
        for non-superusers, without touching form or causing recursion.
        """
        fieldsets = super().get_injected_fieldsets(request, obj)

        # Superusers see everything
        if request.user.is_superuser:
            return fieldsets

        # Fields that should disappear when empty
        hide_if_empty = {
            "external_issue_url",
            "expected_result",
            "actual_result",
        }

        cleaned = []
        for title, opts in fieldsets:
            fields = []
            for name in opts.get("fields", ()):
                if name in hide_if_empty:
                    value = getattr(obj, name, None) if obj else None
                    if not value:
                        continue  # drop field completely
                fields.append(name)

            if fields:
                cleaned.append((title, {**opts, "fields": tuple(fields)}))

        return cleaned


    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)

        class RequestAwareForm(form_class):
            def __new__(cls, *args, **inner_kwargs):
                inner_kwargs["request"] = request
                return form_class(*args, **inner_kwargs)

        return RequestAwareForm

    # ---- display helpers ----
    @display(description="Status")
    def status_display(self, obj):
        return BugStatus[obj.status].label if obj.status else "-"

    @display(description="Severity")
    def severity_display(self, obj):
        return Severity[obj.severity].label if obj.severity else "-"

    @display(description="Reporter Email")
    def reporter_email(self, obj):
        return obj.reporter.email if obj.reporter else "-"

    @display(description="Attachments")
    def attachment_count(self, obj):
        count = obj.attachments.count()
        if not count:
            return "-"
        url = reverse("admin:helpdesk_fileupload_changelist") + f"?object_id={obj.pk}"
        return format_html('<a href="{}"><b>{}</b></a>', url, count)

    @display(description="Attachments")
    def attachments_display(self, obj):
        qs = obj.attachments.all()
        if not qs.exists():
            return "-"

        return format_html(
            "<br>".join(
                f'<a href="{reverse("admin:helpdesk_fileupload_change", args=[f.pk])}" target="_blank">{f.original_name}</a>'
                for f in qs
            )
        )

    # ---- filters ----
    def get_list_filter(self, request):
        if user_is_verified_employee(request):
            return [
                changelist_filter("reporter"),
                changelist_filter("status"),
                changelist_filter("severity"),
                changelist_filter("emails_sent"),
                HasAttachmentsFilter,
            ]
