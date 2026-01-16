import logging

from django import forms
from django.db import transaction
from utilities.utils.general.normalize_text import normalize_text

from invoices.constants import PAYMENT_REFERENCE_MAX_LENGTH, PAYMENT_STATUS_CODES
from invoices.exceptions import InvoiceValidationError
from invoices.models.invoice import Invoice
from invoices.models.payment import Payment
from invoices.models.payment_method import PaymentMethod
from invoices.services.invoice import update_invoice_status
from invoices.services.payment import validate_payment_amount, validate_payment_reference

logger = logging.getLogger(__name__)

class PaymentForm(forms.ModelForm):

    """Form for creating and updating Payment instances."""

    class Meta:
        model = Payment
        fields = ['invoice', 'amount', 'payment_date', 'payment_method', 'payment_reference', 'status']
        widgets = {
            'invoice': forms.Select(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'required': 'required',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter payment amount',
            }),
            'payment_date': forms.DateInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'type': 'date',
            }),
            'payment_method': forms.Select(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
            }),
            'payment_reference': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': PAYMENT_REFERENCE_MAX_LENGTH,
                'placeholder': 'Enter payment reference',
            }),
            'status': forms.Select(choices=[(k, v) for k, v in PAYMENT_STATUS_CODES.items()], attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        logger.debug("Initializing PaymentForm")
        super().__init__(*args, **kwargs)
        self.user = user

        valid_invoice_qs = Invoice.objects.filter(
            deleted_at__isnull=True,
            is_active=True,
            status__code__in=['SENT', 'PARTIALLY_PAID']
        ).select_related('status').order_by('-id')
        if 'invoice' in self.fields:
            if self.instance and self.instance.pk:
                current_invoice_qs = Invoice.objects.filter(pk=self.instance.invoice_id)
                self.fields['invoice'].queryset = (current_invoice_qs | valid_invoice_qs[:50]).distinct()
            else:
                self.fields['invoice'].queryset = valid_invoice_qs[:50]

            self.fields['payment_method'].queryset = PaymentMethod.objects.filter(
                deleted_at__isnull=True, is_active=True
            )

            if 'initial' in kwargs and 'invoice' in kwargs['initial']:
                self.fields['invoice'].initial = kwargs['initial']['invoice']

            if not self.fields['invoice'].queryset.exists():
                logger.warning("No valid invoices available for payment.")
                self.fields['invoice'].widget.attrs['disabled'] = 'disabled'
                self.fields['invoice'].help_text = (
                    "No valid invoices available. Please create an invoice with status SENT or PARTIALLY_PAID."
                )
                self.fields['invoice'].required = False
            else:
                self.fields['invoice'].empty_label = None
                self.fields['invoice'].required = True

    def clean_invoice(self):
        invoice = self.cleaned_data.get('invoice')
        if self.fields['invoice'].required and not invoice:
            raise InvoiceValidationError(
                message="An invoice must be selected.",
                code="invalid_invoice",
                details={"field": "invoice"}
            )
        if invoice:
            if not invoice.is_active:
                raise InvoiceValidationError(
                    message="Invoice must be active.",
                    code="inactive_invoice",
                    details={"field": "invoice", "invoice_id": invoice.id}
                )
            if invoice.status.code not in ['SENT', 'PARTIALLY_PAID']:
                raise InvoiceValidationError(
                    message="Invoice status must be SENT or PARTIALLY_PAID.",
                    code="invalid_status",
                    details={"field": "invoice", "status": invoice.status.code}
                )
            if not self.fields['invoice'].queryset.filter(id=invoice.id).exists():
                raise InvoiceValidationError(
                    message="Selected invoice is not a valid choice.",
                    code="invalid_invoice",
                    details={"field": "invoice", "invoice_id": invoice.id}
                )
        return invoice

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None or amount <= 0:
            raise InvoiceValidationError(
                message="Payment amount must be positive.",
                code="invalid_payment_amount",
                details={"field": "amount", "value": str(amount)}
            )
        return amount

    def clean_payment_date(self):
        payment_date = self.cleaned_data.get('payment_date')
        invoice = self.cleaned_data.get('invoice')
        if payment_date and invoice and payment_date < invoice.issue_date:
            raise InvoiceValidationError(
                message="Payment date cannot be before invoice issue date.",
                code="invalid_payment_date",
                details={"field": "payment_date", "issue_date": invoice.issue_date}
            )
        return payment_date

    def clean_payment_method(self):
        payment_method = self.cleaned_data.get('payment_method')
        if payment_method and not payment_method.is_active:
            raise InvoiceValidationError(
                message="Payment method must be active.",
                code="inactive_payment_method",
                details={"field": "payment_method", "method_code": payment_method.code}
            )
        return payment_method

    def clean_payment_reference(self):
        payment_reference = self.cleaned_data.get('payment_reference')
        if payment_reference:
            payment_reference = normalize_text(payment_reference)
            if len(payment_reference) > PAYMENT_REFERENCE_MAX_LENGTH:
                raise InvoiceValidationError(
                    message=f"Payment reference cannot exceed {PAYMENT_REFERENCE_MAX_LENGTH} characters.",
                    code="invalid_payment_reference",
                    details={"field": "payment_reference", "value": payment_reference}
                )
        return payment_reference

    def clean_status(self):
        status = self.cleaned_data.get('status')
        invoice = self.cleaned_data.get('invoice')
        if status not in dict(PAYMENT_STATUS_CODES):
            raise InvoiceValidationError(
                message=f"Payment status must be one of {list(dict(PAYMENT_STATUS_CODES).keys())}.",
                code="invalid_payment_status",
                details={"field": "status", "value": status}
            )
        if status == 'COMPLETED' and invoice and invoice.status.code not in ['SENT', 'PARTIALLY_PAID', 'PAID']:
            raise InvoiceValidationError(
                message="Cannot mark payment as COMPLETED for invoice not in SENT, PARTIALLY_PAID, or PAID status.",
                code="invalid_payment_status",
                details={"field": "status", "invoice_status": invoice.status.code}
            )
        return status

    def clean(self):
        cleaned_data = super().clean()
        invoice = cleaned_data.get('invoice')
        amount = cleaned_data.get('amount')
        payment_reference = cleaned_data.get('payment_reference')
        payment_method = cleaned_data.get('payment_method')

        if not invoice and self.fields['invoice'].required:
            raise InvoiceValidationError(
                message="An invoice must be selected.",
                code="invalid_invoice",
                details={"field": "invoice"}
            )

        if invoice:
            if invoice.status.code == 'CANCELLED':
                raise InvoiceValidationError(
                    message="Cannot add payment to a cancelled invoice.",
                    code="cancelled_invoice",
                    details={"field": "invoice", "invoice_id": invoice.id}
                )
            try:
                validate_payment_amount(amount, invoice, self.instance.pk if self.instance else None)
                payment_reference = normalize_text(payment_reference) if payment_reference else payment_reference
                validate_payment_reference(
                    payment_reference,
                    payment_method.code if payment_method else None,
                    invoice,
                    self.instance.pk if self.instance else None
                )
            except InvoiceValidationError as e:
                raise InvoiceValidationError(
                    message=str(e),
                    code=e.code,
                    details=e.details
                )

        return cleaned_data

    @transaction.atomic
    def save(self, commit=True, user=None):
        """Override save to set audit fields and update invoice status."""
        logger.debug(f"Saving PaymentForm: {self.cleaned_data.get('payment_reference', 'New Payment')}, user={user}")
        instance = super().save(commit=False)
        if user:
            if not instance.pk:
                instance.created_by = user
            instance.updated_by = user
        if commit:
            if instance.invoice:
                instance.save(user=user)
                update_invoice_status(instance.invoice, user)
            else:
                raise InvoiceValidationError(
                    message="Cannot save payment without a valid invoice.",
                    code="invalid_invoice",
                    details={"field": "invoice"}
                )
        return instance
