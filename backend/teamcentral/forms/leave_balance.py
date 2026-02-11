import logging

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from teamcentral.models import LeaveBalance
from teamcentral.services import EmployeeLifecycleService

logger = logging.getLogger(__name__)


class LeaveBalanceForm(forms.ModelForm):
    class Meta:
        model = LeaveBalance
        fields = ["employee", "leave_type", "year", "balance", "used", "reset_date"]
        widgets = {
            "reset_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        employee = cleaned_data.get("employee")
        leave_type = cleaned_data.get("leave_type")
        year = cleaned_data.get("year")
        balance = cleaned_data.get("balance")
        used = cleaned_data.get("used")
        reset_date = cleaned_data.get("reset_date")

        if employee and leave_type and year and EmployeeLifecycleService.is_duplicate_balance(
            employee, leave_type, year, exclude_pk=self.instance.pk
        ):
            raise ValidationError("Leave balance already exists for this year.")

        if balance is not None and used is not None and balance < used:
            raise ValidationError({"balance": "Used leave cannot exceed balance."})

        if year and year > timezone.now().year + 1:
            raise ValidationError({"year": "Year cannot be more than one year in the future."})

        if reset_date and year and reset_date.year != year:
            raise ValidationError({"reset_date": "Reset date must be in the same year."})

        return cleaned_data
