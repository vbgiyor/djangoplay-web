from datetime import date, datetime

from django import forms
from django.utils import timezone

from helpdesk.models import SupportStatus, SupportTicket


class SupportForm(forms.ModelForm):
    resolved_at = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = SupportTicket
        exclude = (
            "id", "ticket_number", "emails_sent", "client_ip",
            "deleted_at", "deleted_by",
            "created_at", "updated_at",
            "created_by", "updated_by", "history",
        )

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        resolved_date = self.cleaned_data.get("resolved_at")

        if isinstance(resolved_date, date):
            instance.resolved_at = timezone.make_aware(
                datetime.combine(resolved_date, datetime.min.time())
            )
        elif instance.status in (SupportStatus.RESOLVED, SupportStatus.CLOSED):
            instance.resolved_at = timezone.now()

        if commit:
            instance.save(user=user)
            self.save_m2m()

        return instance
