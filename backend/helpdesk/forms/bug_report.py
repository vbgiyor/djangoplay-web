from datetime import date, datetime

from django import forms
from django.utils import timezone

from helpdesk.models import BugReport, BugStatus


class BugReportForm(forms.ModelForm):

    """
    BugReport form.
    Owns:
    - Visibility / editability rules
    - Business logic
    """

    resolved_at = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Optional: mark the bug as resolved on this date.",
    )

    class Meta:
        model = BugReport
        exclude = (
            "id",
            "bug_number",
            "history",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        user = getattr(self.request, "user", None)

        for name in ("external_issue_url", "expected_result", "actual_result"):
            field = self.fields.get(name)
            if not field:
                continue

            value = (
                getattr(self.instance, name, None)
                if self.instance and self.instance.pk
                else None
            )

            # Superusers: full control
            if user and user.is_superuser:
                continue

            # Non-superusers: read-only logic
            field.disabled = True
            field.required = False

            if value:
                # value exists → show read-only
                continue

            if name == "external_issue_url":
                # visible + explanatory text
                field.help_text = "No URL provided"
            else:
                # expected_result / actual_result → hide if empty
                field.widget = forms.HiddenInput()

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        resolved_date = self.cleaned_data.get("resolved_at")

        if isinstance(resolved_date, date):
            instance.status = BugStatus.RESOLVED
            instance.resolved_at = timezone.make_aware(
                datetime.combine(resolved_date, datetime.min.time())
            )
        elif instance.status == BugStatus.RESOLVED and not instance.resolved_at:
            instance.resolved_at = timezone.now()

        if commit:
            instance.save(user=user)
            self.save_m2m()

        return instance
