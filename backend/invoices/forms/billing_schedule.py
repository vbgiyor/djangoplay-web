import logging

from django import forms
from django.db import transaction
from entities.models import Entity
from utilities.utils.general.normalize_text import normalize_text

from invoices.constants import BILLING_FREQUENCY_CHOICES, BILLING_STATUS_CODES, DESCRIPTION_MAX_LENGTH
from invoices.exceptions import InvoiceValidationError
from invoices.models.billing_schedule import BillingSchedule
from invoices.services.billing_schedule import validate_billing_schedule

ENTITY_DROPDOWN_LIMIT = 50

logger = logging.getLogger(__name__)

class BillingScheduleForm(forms.ModelForm):

    """Form for creating and updating BillingSchedule instances."""

    class Meta:
        model = BillingSchedule
        fields = [
            'entity', 'description', 'frequency', 'start_date', 'end_date',
            'next_billing_date', 'amount',  'status'
        ]
        widgets = {
            'entity': forms.Select(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
            }),
            'description': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': DESCRIPTION_MAX_LENGTH,
                'placeholder': 'Enter billing schedule description',
            }),
            'frequency': forms.Select(choices=BILLING_FREQUENCY_CHOICES, attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'type': 'date',
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'type': 'date',
            }),
            'next_billing_date': forms.DateInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'type': 'date',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter billing amount',
            }),
            'status': forms.Select(choices=[(k, v) for k, v in BILLING_STATUS_CODES.items()], attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        logger.debug("Initializing BillingScheduleForm")
        super().__init__(*args, **kwargs)
        self.user = user

        if 'entity' in self.fields:
            qs = Entity.objects.filter(is_active=True).select_related('default_address')

            if self.instance and self.instance.pk and self.instance.entity_id:
                self.fields['entity'].queryset = (
                    qs.filter(pk=self.instance.entity_id) |
                    qs.order_by('-id')[:ENTITY_DROPDOWN_LIMIT]
                )
            else:
                self.fields['entity'].queryset = qs.order_by('-id')[:ENTITY_DROPDOWN_LIMIT]


    def clean_entity(self):
        entity = self.cleaned_data.get('entity')
        if not entity:
            raise InvoiceValidationError(
                message="Entity is required.",
                code="inactive_entity",
                details={"field": "entity"}
            )
        if not entity.is_active:
            raise InvoiceValidationError(
                message="Entity must be active.",
                code="inactive_entity",
                details={"field": "entity", "entity_id": entity.id}
            )
        return entity

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if not description or not description.strip():
            raise InvoiceValidationError(
                message="Description cannot be empty or whitespace.",
                code="invalid_description",
                details={"field": "description"}
            )
        description = normalize_text(description)
        if len(description) > DESCRIPTION_MAX_LENGTH:
            raise InvoiceValidationError(
                message=f"Description cannot exceed {DESCRIPTION_MAX_LENGTH} characters.",
                code="invalid_description",
                details={"field": "description", "value": description}
            )
        return description

    def clean_frequency(self):
        frequency = self.cleaned_data.get('frequency')
        if frequency not in dict(BILLING_FREQUENCY_CHOICES):
            raise InvoiceValidationError(
                message=f"Frequency must be one of {list(dict(BILLING_FREQUENCY_CHOICES).keys())}.",
                code="invalid_frequency",
                details={"field": "frequency", "value": frequency}
            )
        return frequency

    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')
        if not start_date:
            raise InvoiceValidationError(
                message="Start date is required.",
                code="invalid_date",
                details={"field": "start_date"}
            )
        return start_date

    def clean_end_date(self):
        end_date = self.cleaned_data.get('end_date')
        start_date = self.cleaned_data.get('start_date')
        if end_date and start_date and end_date < start_date:
            raise InvoiceValidationError(
                message="End date cannot be before start date.",
                code="invalid_end_date",
                details={"field": "end_date", "start_date": start_date, "end_date": end_date}
            )
        return end_date

    def clean_next_billing_date(self):
        next_billing_date = self.cleaned_data.get('next_billing_date')
        start_date = self.cleaned_data.get('start_date')
        end_date = self.cleaned_data.get('end_date')
        if not next_billing_date:
            raise InvoiceValidationError(
                message="Next billing date is required.",
                code="invalid_next_billing_date",
                details={"field": "next_billing_date"}
            )
        if next_billing_date and start_date and next_billing_date < start_date:
            raise InvoiceValidationError(
                message="Next billing date cannot be before start date.",
                code="invalid_next_billing_date",
                details={"field": "next_billing_date", "start_date": start_date}
            )
        if next_billing_date and end_date and next_billing_date > end_date:
            raise InvoiceValidationError(
                message="Next billing date cannot be after end date.",
                code="invalid_next_billing_date",
                details={"field": "next_billing_date", "end_date": end_date}
            )
        return next_billing_date

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None or amount <= 0:
            raise InvoiceValidationError(
                message="Billing amount must be positive.",
                code="invalid_billing_amount",
                details={"field": "amount", "value": str(amount)}
            )
        return amount

    def clean_status(self):
        status = self.cleaned_data.get('status')
        if status not in dict(BILLING_STATUS_CODES):
            raise InvoiceValidationError(
                message=f"Status must be one of {list(dict(BILLING_STATUS_CODES).keys())}.",
                code="invalid_billing_status",
                details={"field": "status", "value": status}
            )
        end_date = self.cleaned_data.get('end_date')
        if status == 'COMPLETED' and not end_date:
            raise InvoiceValidationError(
                message="Completed billing schedules must have an end date.",
                code="invalid_billing_status",
                details={"field": "status", "value": status}
            )
        return status

    def clean(self):
        cleaned_data = super().clean()
        instance = self.instance if self.instance and self.instance.pk else BillingSchedule(**cleaned_data)
        try:
            validate_billing_schedule(instance, exclude_pk=self.instance.pk if self.instance else None)
        except InvoiceValidationError as e:
            raise InvoiceValidationError(
                message=str(e),
                code=e.code,
                details=e.details
            )
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True, user=None):
        """Override save to set audit fields and use atomic transaction."""
        logger.debug(f"Saving BillingScheduleForm: {self.cleaned_data.get('description', 'New Billing Schedule')}, user={user}")
        instance = super().save(commit=False)
        if user:
            if not instance.pk:
                instance.created_by = user
            instance.updated_by = user
        if commit:
            instance.save(user=user)
        return instance
