import logging

from django import forms
from django.core.exceptions import ValidationError
from users.models import Employee
from users.models.address import Address
from users.models.user_activity_log import UserActivityLog

logger = logging.getLogger(__name__)


class AddressForm(forms.ModelForm):

    """
    Address admin form.

    ADD:
      - Show searchable Email field (Select2)
    EDIT:
      - Show Email as read-only text
    """

    user = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True, deleted_at__isnull=True),
        widget=forms.Select(attrs={"class": "select2"}),
        label="Email",
        required=False,
        help_text="Employee owning this address",
    )

    email = forms.EmailField(
        label="Email",
        required=False,
        disabled=True,
    )

    class Meta:
        model = Address
        exclude = (
            "id",
            "owner",
            "deleted_at",
            "deleted_by",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "history",
        )
        labels = {
            "address": "Street",
        }
        widgets = {
            "address": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            # EDIT → hide search, show read-only email
            self.fields["user"].widget = forms.HiddenInput()
            self.fields["email"].initial = self.instance.owner.email
        else:
            # ADD → hide read-only email
            self.fields["email"].widget = forms.HiddenInput()

    def clean(self):
        cleaned = super().clean()

        if not self.instance.pk and not cleaned.get("user"):
            raise ValidationError("Email is required.")

        if not cleaned.get("address"):
            raise ValidationError("Address is required.")

        return cleaned


class UserActivityLogForm(forms.ModelForm):

    """Form for UserActivityLog model (read-only)."""

    user = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True, deleted_at__isnull=True),
        required=True,
        help_text="Employee who performed the action"
    )

    class Meta:
        model = UserActivityLog
        fields = ['user', 'action', 'client_ip']
        widgets = {
            'user': forms.Select(),
            'action': forms.Select(choices=UserActivityLog.ACTION_CHOICES),
            'client_ip': forms.TextInput(),
            'created_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].disabled = True  # Read-only form
