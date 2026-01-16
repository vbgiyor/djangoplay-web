import logging

from django import forms
from django.db import transaction
from locations.models import CustomRegion
from utilities.utils.general.normalize_text import normalize_text

from invoices.constants import DESCRIPTION_MAX_LENGTH, GST_RATE_TYPE_CHOICES
from invoices.exceptions import GSTValidationError
from invoices.models.gst_configuration import GSTConfiguration

logger = logging.getLogger(__name__)

class GSTConfigurationForm(forms.ModelForm):

    """Form for creating and updating GSTConfiguration instances."""

    class Meta:
        model = GSTConfiguration
        fields = [
            'description', 'cgst_rate', 'sgst_rate', 'igst_rate',
            'rate_type', 'applicable_region', 'effective_from', 'effective_to',
            'cgst_amount', 'sgst_amount', 'igst_amount'
        ]
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': DESCRIPTION_MAX_LENGTH,
                'placeholder': 'Enter GST configuration description',
            }),
            'cgst_rate': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter CGST rate',
            }),
            'sgst_rate': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter SGST rate',
            }),
            'igst_rate': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter IGST rate',
            }),
            'cgst_amount': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0',
                'placeholder': 'CGST amount (must be 0)',
                'readonly': True,
            }),
            'sgst_amount': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0',
                'placeholder': 'SGST amount (must be 0)',
                'readonly': True,
            }),
            'igst_amount': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0',
                'placeholder': 'IGST amount (must be 0)',
                'readonly': True,
            }),
            'rate_type': forms.Select(choices=GST_RATE_TYPE_CHOICES, attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
            }),
            'applicable_region': forms.Select(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
            }),
            'effective_from': forms.DateInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'type': 'date',
            }),
            'effective_to': forms.DateInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'type': 'date',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        logger.debug("Initializing GSTConfigurationForm")
        super().__init__(*args, **kwargs)
        self.user = user

        if 'applicable_region' in self.fields:
            qs = CustomRegion.objects.filter(is_active=True).select_related('country')

            if self.instance and self.instance.pk and self.instance.applicable_region:
                self.fields['applicable_region'].queryset = qs.filter(id=self.instance.applicable_region.id)
            else:
                self.fields['applicable_region'].queryset = qs.order_by('id')


    def clean_description(self):
        description = self.cleaned_data.get('description')
        if not description or not description.strip():
            raise GSTValidationError(
                message="Description cannot be empty or whitespace.",
                code="invalid_description",
                details={"field": "description"}
            )
        description = normalize_text(description)
        if len(description) > DESCRIPTION_MAX_LENGTH:
            raise GSTValidationError(
                message=f"Description cannot exceed {DESCRIPTION_MAX_LENGTH} characters.",
                code="invalid_description",
                details={"field": "description", "value": description}
            )
        return description

    def clean_cgst_amount(self):
        cgst_amount = self.cleaned_data.get('cgst_amount')
        if cgst_amount != 0:
            raise GSTValidationError(
                message="CGST amount must be zero for GST configurations.",
                code="invalid_cgst_amount",
                details={"field": "cgst_amount", "value": str(cgst_amount)}
            )
        return cgst_amount

    def clean_sgst_amount(self):
        sgst_amount = self.cleaned_data.get('sgst_amount')
        if sgst_amount != 0:
            raise GSTValidationError(
                message="SGST amount must be zero for GST configurations.",
                code="invalid_sgst_amount",
                details={"field": "sgst_amount", "value": str(sgst_amount)}
            )
        return sgst_amount

    def clean_igst_amount(self):
        igst_amount = self.cleaned_data.get('igst_amount')
        if igst_amount != 0:
            raise GSTValidationError(
                message="IGST amount must be zero for GST configurations.",
                code="invalid_igst_amount",
                details={"field": "igst_amount", "value": str(igst_amount)}
            )
        return igst_amount

    def clean_effective_from(self):
        effective_from = self.cleaned_data.get('effective_from')
        if not effective_from:
            raise GSTValidationError(
                message="Effective start date is required.",
                code="invalid_effective_dates",
                details={"field": "effective_from"}
            )
        return effective_from

    def clean_effective_to(self):
        effective_to = self.cleaned_data.get('effective_to')
        effective_from = self.cleaned_data.get('effective_from')
        if effective_to and effective_from and effective_to < effective_from:
            raise GSTValidationError(
                message="Effective end date cannot be before effective start date.",
                code="invalid_effective_dates",
                details={"field": "effective_to", "effective_from": effective_from, "effective_to": effective_to}
            )
        return effective_to

    def clean(self):
        cleaned_data = super().clean()
        from invoices.services import validate_gst_configuration
        instance = self.instance if self.instance and self.instance.pk else GSTConfiguration(**cleaned_data)
        try:
            validate_gst_configuration(instance, exclude_pk=self.instance.pk if self.instance else None)
        except GSTValidationError as e:
            raise GSTValidationError(
                message=str(e),
                code=e.code,
                details=e.details
            )
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True, user=None):
        """Override save to set audit fields."""
        logger.debug(f"Saving GSTConfigurationForm: {self.cleaned_data.get('description', 'New GST Config')}, user={user}")
        instance = super().save(commit=False)
        if user:
            if not instance.pk:
                instance.created_by = user
            instance.updated_by = user
        if commit:
            instance.save(user=user)
        return instance
