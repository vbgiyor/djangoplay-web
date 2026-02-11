from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from utilities.utils.locations.phone_number_validations import validate_phone_number

from teamcentral.models import MemberProfile
from teamcentral.services import MemberLifecycleService

User = get_user_model()


class MemberProfileForm(forms.ModelForm):
    employee = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True, deleted_at__isnull=True),
        required=True,
    )

    class Meta:
        model = MemberProfile
        fields = [
            "email", "first_name", "last_name", "phone_number",
            "address", "status", "is_active", "employee",
        ]

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        phone = cleaned_data.get("phone_number")
        employee = cleaned_data.get("employee")

        if email and MemberLifecycleService.is_duplicate_email(email, exclude_pk=self.instance.pk):
            raise ValidationError({"email": "Email already exists."})

        if phone and not validate_phone_number(phone):
            raise ValidationError({"phone_number": "Invalid phone number format."})

        if employee and MemberProfile.objects.filter(
            employee=employee, deleted_at__isnull=True
        ).exclude(pk=self.instance.pk).exists():
            raise ValidationError({"employee": "Employee already linked to another member."})

        return cleaned_data
