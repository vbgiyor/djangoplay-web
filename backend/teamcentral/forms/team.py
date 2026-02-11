import logging

from django import forms
from django.core.exceptions import ValidationError

from teamcentral.models import Team

logger = logging.getLogger(__name__)


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["name", "department", "leader", "description", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        department = cleaned_data.get("department")
        leader = cleaned_data.get("leader")

        if name and department and Team.objects.filter(
            name__iexact=name,
            department=department,
            deleted_at__isnull=True,
        ).exclude(pk=self.instance.pk).exists():
            raise ValidationError({"name": "Team name already exists in this department."})

        if leader and department and leader.department != department:
            raise ValidationError({"leader": "Leader must be in the same department."})

        return cleaned_data
