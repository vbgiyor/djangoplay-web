import logging

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from teamcentral.models import LeaveApplication
from teamcentral.services import EmployeeLifecycleService

User = get_user_model()

logger = logging.getLogger(__name__)


class LeaveApplicationForm(forms.ModelForm):
    class Meta:
        model = LeaveApplication
        fields = [
            "employee", "leave_type", "start_date", "end_date",
            "hours", "reason", "status", "approver"
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "reason": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = timezone.now().date()
        self.fields["approver"].queryset = User.objects.filter(
            employment_status__code="ACTV",
            hire_date__lte=today,
            termination_date__isnull=True,
        )

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start_date")
        end = cleaned_data.get("end_date")
        hours = cleaned_data.get("hours")
        employee = cleaned_data.get("employee")
        leave_type = cleaned_data.get("leave_type")

        if start and end and start > end:
            raise ValidationError({"end_date": "End date must be after start date."})

        if hours and hours <= 0:
            raise ValidationError({"hours": "Hours must be positive."})

        if hours and end:
            raise ValidationError({"hours": "Cannot specify both hours and end date."})

        if employee and leave_type and start:
            if not EmployeeLifecycleService.has_sufficient_balance(
                employee, leave_type, start, end or start
            ):
                raise ValidationError("Insufficient leave balance.")

        return cleaned_data
