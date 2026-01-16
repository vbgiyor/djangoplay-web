import logging
import re

from django import forms
from django.db import transaction
from utilities.utils.general.normalize_text import normalize_text

from invoices.constants import DESCRIPTION_MAX_LENGTH, PAYMENT_METHOD_CODE_MAX_LENGTH, PAYMENT_METHOD_NAME_MAX_LENGTH
from invoices.exceptions import InvoiceValidationError
from invoices.models.payment_method import PaymentMethod
from invoices.services.payment import validate_payment_method

logger = logging.getLogger(__name__)

class PaymentMethodForm(forms.ModelForm):

    """Form for creating and updating PaymentMethod instances."""

    class Meta:
        model = PaymentMethod
        fields = ['code', 'name', 'description', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': PAYMENT_METHOD_CODE_MAX_LENGTH,
                'placeholder': 'Enter payment method code',
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': PAYMENT_METHOD_NAME_MAX_LENGTH,
                'placeholder': 'Enter payment method name',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'rows': 4,
                'placeholder': 'Enter description',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        logger.debug("Initializing PaymentMethodForm")
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code or not code.strip():
            raise InvoiceValidationError(
                message="Payment method code is required.",
                code="invalid_payment_method_code",
                details={"field": "code"}
            )
        code = normalize_text(code)
        if len(code) > PAYMENT_METHOD_CODE_MAX_LENGTH:
            raise InvoiceValidationError(
                message=f"Payment method code cannot exceed {PAYMENT_METHOD_CODE_MAX_LENGTH} characters.",
                code="invalid_payment_method_code",
                details={"field": "code", "value": code}
            )
        if not re.match(r'^[a-zA-Z0-9_]+$', code):
            raise InvoiceValidationError(
                message="Payment method code must be alphanumeric or contain underscores.",
                code="invalid_payment_method_code",
                details={"field": "code", "value": code}
            )
        if PaymentMethod.objects.filter(code=code, is_active=True, deleted_at__isnull=True).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise InvoiceValidationError(
                message="Payment method code already exists.",
                code="duplicate_payment_method_code",
                details={"field": "code", "value": code}
            )
        return code

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name or not name.strip():
            raise InvoiceValidationError(
                message="Payment method name is required.",
                code="invalid_payment_method_name",
                details={"field": "name"}
            )
        name = normalize_text(name)
        if len(name) > PAYMENT_METHOD_NAME_MAX_LENGTH:
            raise InvoiceValidationError(
                message=f"Payment method name cannot exceed {PAYMENT_METHOD_NAME_MAX_LENGTH} characters.",
                code="invalid_payment_method_name",
                details={"field": "name", "value": name}
            )
        return name

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description:
            description = normalize_text(description)
            if len(description) > DESCRIPTION_MAX_LENGTH:
                raise InvoiceValidationError(
                    message=f"Description cannot exceed {DESCRIPTION_MAX_LENGTH} characters.",
                    code="invalid_description",
                    details={"field": "description", "value": description}
                )
        return description

    def clean(self):
        cleaned_data = super().clean()
        instance = self.instance if self.instance and self.instance.pk else PaymentMethod(**cleaned_data)
        try:
            validate_payment_method(instance, exclude_pk=self.instance.pk if self.instance else None)
        except InvoiceValidationError as e:
            raise InvoiceValidationError(
                message=str(e),
                code=e.code,
                details=e.details
            )
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True, user=None):
        """Override save to set audit fields."""
        logger.debug(f"Saving PaymentMethodForm: {self.cleaned_data.get('code', 'New Payment Method')}, user={user}")
        instance = super().save(commit=False)
        if user:
            if not instance.pk:
                instance.created_by = user
            instance.updated_by = user
        if commit:
            instance.save(user=user)
        return instance
