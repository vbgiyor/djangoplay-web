import logging

from django import forms
from django.core.exceptions import ValidationError

from teamcentral.models import LeaveType

logger = logging.getLogger(__name__)


class LeaveTypeForm(forms.ModelForm):
    class Meta:
        model = LeaveType
        fields = ["code", "name", "default_balance", "is_active"]

    def clean(self):
        cleaned_data = super().clean()
        code = cleaned_data.get("code")
        name = cleaned_data.get("name")
        default_balance = cleaned_data.get("default_balance")

        if code and LeaveType.objects.filter(
            code__iexact=code, deleted_at__isnull=True
        ).exclude(pk=self.instance.pk).exists():
            raise ValidationError({"code": "Leave type code already exists."})

        if name and LeaveType.objects.filter(
            name__iexact=name, deleted_at__isnull=True
        ).exclude(pk=self.instance.pk).exists():
            raise ValidationError({"name": "Leave type name already exists."})

        if default_balance is not None and default_balance < 0:
            raise ValidationError({"default_balance": "Default balance cannot be negative."})

        return cleaned_data
