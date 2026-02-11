from datetime import timedelta

from django import forms
from django.utils import timezone

from users.models import Employee, PasswordResetRequest


class PasswordResetRequestForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True, deleted_at__isnull=True)
    )

    class Meta:
        model = PasswordResetRequest
        fields = ["user", "used"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is None:
            self.fields.pop("used", None)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.pk:
            instance.expires_at = timezone.now() + timedelta(hours=24)
        if commit:
            instance.save()
        return instance
