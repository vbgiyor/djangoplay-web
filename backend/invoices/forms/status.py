import logging

from django import forms
from django.db import transaction
from utilities.utils.general.normalize_text import normalize_text

from invoices.constants import STATUS_CODE_MAX_LENGTH, STATUS_NAME_MAX_LENGTH
from invoices.exceptions import InvoiceValidationError
from invoices.models.status import Status

logger = logging.getLogger(__name__)

class StatusForm(forms.ModelForm):

    """Form for creating and updating Status instances."""

    class Meta:
        model = Status
        fields = ['name', 'code', 'is_default', 'is_locked']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': STATUS_NAME_MAX_LENGTH,
                'placeholder': 'Enter status name',
            }),
            'code': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': STATUS_CODE_MAX_LENGTH,
                'placeholder': 'Enter status code',
            }),
            'is_default': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded',
            }),
            'is_locked': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        logger.debug("Initializing StatusForm")
        super().__init__(*args, **kwargs)
        self.user = user
        self.skip_validation = False  # Default to False

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name or not name.strip():
            raise InvoiceValidationError(
                message="Status name cannot be empty or whitespace.",
                code="empty_name",
                details={"field": "name"}
            )
        name = normalize_text(name)
        if len(name) > STATUS_NAME_MAX_LENGTH:
            raise InvoiceValidationError(
                message=f"Status name cannot exceed {STATUS_NAME_MAX_LENGTH} characters.",
                code="invalid_name",
                details={"field": "name", "value": name}
            )
        return name

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code or not code.strip():
            raise InvoiceValidationError(
                message="Status code cannot be empty or whitespace.",
                code="empty_code",
                details={"field": "code"}
            )
        code = normalize_text(code)
        if len(code) > STATUS_CODE_MAX_LENGTH:
            raise InvoiceValidationError(
                message=f"Status code cannot exceed {STATUS_CODE_MAX_LENGTH} characters.",
                code="invalid_code",
                details={"field": "code", "value": code}
            )
        return code

    def clean(self):
        if self.skip_validation:
            logger.debug("Skipping form validation for GET request")
            return self.cleaned_data
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        code = cleaned_data.get('code')
        is_default = cleaned_data.get('is_default')

        if name and code:
            from invoices.services import validate_status
            instance = self.instance if self.instance and self.instance.pk else Status()
            instance.name = name
            instance.code = code
            instance.is_default = is_default
            instance.is_locked = cleaned_data.get('is_locked', False)
            try:
                validate_status(instance, exclude_pk=self.instance.pk if self.instance else None)
            except InvoiceValidationError as e:
                raise InvoiceValidationError(
                    message=str(e),
                    code=e.code,
                    details=e.details
                )

        return cleaned_data

    def full_clean(self):
        if self.skip_validation:
            self.cleaned_data = {}
            self._errors = {}
            logger.debug("Skipping full_clean for GET request")
            return
        super().full_clean()

    @transaction.atomic
    def save(self, commit=True, user=None):
        logger.debug(f"Saving StatusForm: {self.cleaned_data.get('name', 'New Status')}, user={user}")
        instance = super().save(commit=False)
        if user:
            if not instance.pk:
                instance.created_by = user
            instance.updated_by = user
        if commit:
            instance.save(user=user)
        return instance
