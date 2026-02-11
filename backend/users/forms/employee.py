import logging

from django import forms

from users.models import Employee

logger = logging.getLogger(__name__)


class EmployeeForm(forms.ModelForm):

    """
    Form for creating/updating Employee instances.
    """

    class Meta:
        model = Employee
        exclude = (
            "id",
            "employee_code",
            "address_display",
            "deleted_at",
            "deleted_by",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "history",
        )
        widgets = {
            "hire_date": forms.DateInput(attrs={"type": "date"}),
            "termination_date": forms.DateInput(attrs={"type": "date"}),
            "probation_end_date": forms.DateInput(attrs={"type": "date"}),
            "contract_end_date": forms.DateInput(attrs={"type": "date"}),
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self._user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            logger.warning("EmployeeForm errors: %s", self.errors.as_json())
        return cleaned_data

    def save(self, commit=True, user=None):
        effective_user = user or self._user
        instance = super().save(commit=False)

        if commit:
            instance.save(user=effective_user)
            self.save_m2m()

        return instance
