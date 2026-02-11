from django import forms
from django.core.exceptions import ValidationError

from teamcentral.models import MemberStatus


class MemberStatusForm(forms.ModelForm):
    class Meta:
        model = MemberStatus
        fields = ["code", "name", "is_active"]

    def clean(self):
        cleaned_data = super().clean()
        code = cleaned_data.get("code")
        name = cleaned_data.get("name")

        if code and MemberStatus.objects.filter(
            code__iexact=code, deleted_at__isnull=True
        ).exclude(pk=self.instance.pk).exists():
            raise ValidationError({"code": "Status code already exists."})

        if name and MemberStatus.objects.filter(
            name__iexact=name, deleted_at__isnull=True
        ).exclude(pk=self.instance.pk).exists():
            raise ValidationError({"name": "Status name already exists."})

        return cleaned_data
