import logging
from decimal import Decimal

import redis
from core.utils.redis_client import redis_client
from django import forms
from django.db import transaction
from utilities.utils.general.normalize_text import normalize_text

from invoices.constants import (
    DESCRIPTION_MAX_LENGTH,
    GSTIN_MAX_LENGTH,
    INVOICE_NUMBER_MAX_LENGTH,
    PAYMENT_METHOD_CODES,
    PAYMENT_REFERENCE_MAX_LENGTH,
    PAYMENT_TERMS_CHOICES,
    TAX_EXEMPTION_CHOICES,
)
from invoices.exceptions import GSTValidationError, InvoiceValidationError
from invoices.models.invoice import Invoice
from invoices.models.line_item import LineItem
from invoices.services import calculate_total_amount
from invoices.services.invoice import generate_invoice_number, get_currency_choices
from invoices.services.line_item import calculate_line_item_total

INVOICE_DROPDOWN_LIMIT = 5

logger = logging.getLogger(__name__)

class InvoiceForm(forms.ModelForm):

    """Form for creating and updating Invoice instances."""

    class Meta:
        model = Invoice
        fields = [
            'invoice_number', 'description', 'issue_date', 'due_date', 'status',
            'payment_terms', 'currency', 'base_amount', 'total_amount',
            'tax_exemption_status', 'payment_method', 'payment_reference',
            'issuer_gstin', 'recipient_gstin',
        ]
        widgets = {
            'invoice_number': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': INVOICE_NUMBER_MAX_LENGTH,
                'placeholder': 'Enter invoice number (auto-generated if blank)',
            }),
            'description': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': DESCRIPTION_MAX_LENGTH,
                'placeholder': 'Enter invoice description',
            }),

            'issue_date': forms.DateInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'type': 'date',
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'type': 'date',
            }),
            'status': forms.Select(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
            }),
            'payment_terms': forms.Select(choices=PAYMENT_TERMS_CHOICES, attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
            }),
            'currency': forms.Select(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
            }),
            'base_amount': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter base amount',
            }),
            'total_amount': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Total amount (calculated)',
                'readonly': True,
            }),
            'tax_exemption_status': forms.Select(choices=TAX_EXEMPTION_CHOICES, attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
            }),
            'payment_method': forms.Select(choices=[(k, v) for k, v in PAYMENT_METHOD_CODES.items()], attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
            }),
            'payment_reference': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': PAYMENT_REFERENCE_MAX_LENGTH,
                'placeholder': 'Enter payment reference',
            }),
            'issuer_gstin': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': GSTIN_MAX_LENGTH,
                'placeholder': 'Enter issuer GSTIN',
            }),
            'recipient_gstin': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': GSTIN_MAX_LENGTH,
                'placeholder': 'Enter recipient GSTIN',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['currency'].choices = get_currency_choices()

        # Map of fields to filtering kwargs and `.only(...)` values
        filter_config = {
            'issuer': {'filter': {'is_active': True}, 'only': ['id', 'name']},
            'recipient': {'filter': {'is_active': True}, 'only': ['id', 'name']},
            'billing_address': {'filter': {'is_active': True}, 'only': ['id', 'city__name']},
            'billing_country': {'filter': {'is_active': True}, 'only': ['id', 'country_code']},
            'billing_region': {'filter': {'is_active': True}, 'only': ['id', 'name']},
        }

        for field_name, config in filter_config.items():
            if field_name in self.fields:
                qs = self.fields[field_name].queryset
                qs = qs.filter(**config['filter']).only(*config['only'])
                self.fields[field_name].queryset = qs


    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     if 'issuer' in self.fields:
    #         self.fields['issuer'].queryset = self.fields['issuer'].queryset.filter(is_active=True).only('id', 'name')
    #     self.fields['recipient'].queryset = self.fields['recipient'].queryset.filter(is_active=True).only('id', 'name')
    #     self.fields['billing_address'].queryset = self.fields['billing_address'].queryset.filter(is_active=True).only('id', 'city__name')
    #     self.fields['billing_country'].queryset = self.fields['billing_country'].queryset.filter(is_active=True).only('id', 'country_code')
    #     self.fields['billing_region'].queryset = self.fields['billing_region'].queryset.filter(is_active=True).only('id', 'name')

    def clean_issuer_gstin(self):
        issuer_gstin = self.cleaned_data.get('issuer_gstin')
        if issuer_gstin:
            issuer_gstin = normalize_text(issuer_gstin)
            try:
                from utilities.utils.entities.entity_validations import validate_gstin
                validate_gstin(issuer_gstin)
            except Exception as e:
                raise GSTValidationError(
                    message=f"Invalid issuer GSTIN: {str(e)}",
                    code="invalid_issuer_gstin",
                    details={"field": "issuer_gstin", "value": issuer_gstin}
                )
        return issuer_gstin

    def clean_recipient_gstin(self):
        recipient_gstin = self.cleaned_data.get('recipient_gstin')
        if recipient_gstin:
            recipient_gstin = normalize_text(recipient_gstin)
            try:
                from utilities.utils.entities.entity_validations import validate_gstin
                validate_gstin(recipient_gstin)
            except Exception as e:
                raise GSTValidationError(
                    message=f"Invalid recipient GSTIN: {str(e)}",
                    code="invalid_recipient_gstin",
                    details={"field": "recipient_gstin", "value": recipient_gstin}
                )
        return recipient_gstin

    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        issue_date = self.cleaned_data.get('issue_date')
        if due_date and issue_date and due_date < issue_date:
            raise InvoiceValidationError(
                message="Due date cannot be before issue date.",
                code="invalid_due_date",
                details={"field": "due_date", "issue_date": issue_date, "due_date": due_date}
            )
        return due_date

    def clean_status(self):
        status = self.cleaned_data.get('status')
        if status and (not status.is_active or status.deleted_at is not None):
            raise InvoiceValidationError(
                message="Invoice status must be active.",
                code="inactive_status",
                details={"field": "status", "status_id": status.id}
            )
        return status

    def clean_base_amount(self):
        base_amount = self.cleaned_data.get('base_amount')
        if base_amount is not None and base_amount < 0:
            raise InvoiceValidationError(
                message="Base amount cannot be negative.",
                code="invalid_base_amount",
                details={"field": "base_amount", "value": str(base_amount)}
            )
        return base_amount

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

    def clean(self):
        cleaned_data = super().clean()
        billing_country = cleaned_data.get('billing_country')
        tax_exemption_status = cleaned_data.get('tax_exemption_status')
        cgst_rate = cleaned_data.get('cgst_rate')
        sgst_rate = cleaned_data.get('sgst_rate')
        igst_rate = cleaned_data.get('igst_rate')
        billing_region = cleaned_data.get('billing_region')
        issue_date = cleaned_data.get('issue_date')
        hsn_sac_code = cleaned_data.get('hsn_sac_code')

        # Validate GST fields for India
        if billing_country and billing_country.country_code.upper() == 'IN':
            if tax_exemption_status not in ['EXEMPT', 'ZERO_RATED']:
                from invoices.services.gst_configuration import validate_gst_rates
                try:
                    validate_gst_rates(
                        cgst_rate=cgst_rate,
                        sgst_rate=sgst_rate,
                        igst_rate=igst_rate,
                        region_id=billing_region.id if billing_region else None,
                        country_id=billing_country.id,
                        issue_date=issue_date,
                        tax_exemption_status=tax_exemption_status,
                        hsn_sac_code=hsn_sac_code
                    )
                except GSTValidationError as e:
                    raise InvoiceValidationError(
                        message=str(e),
                        code="gst_validation_error",
                        details={"error": str(e)}
                    )

        return cleaned_data

    @transaction.atomic
    def save(self, commit=True, user=None):
        logger.debug(f"Saving InvoiceForm: {self.cleaned_data.get('invoice_number', 'New Invoice')}, user={user}")
        instance = super().save(commit=False)
        if not instance.invoice_number:
            instance.invoice_number = generate_invoice_number()

        # Invalidate invoice total cache to ensure fresh calculation
        cache_key = f"invoice:{instance.id or 'new'}:total_amount"
        try:
            redis_client.delete(cache_key)
            logger.debug(f"Invalidated cache for Invoice: {cache_key}")
        except redis.RedisError as e:
            logger.warning(f"Failed to invalidate cache for {cache_key}: {str(e)}")

        # Update associated line items' GST rates and totals
        if instance.pk:
            line_items = LineItem.objects.filter(invoice=instance, is_active=True, deleted_at__isnull=True)
            for line_item in line_items:
                line_item.cgst_rate = instance.cgst_rate
                line_item.sgst_rate = instance.sgst_rate
                line_item.igst_rate = instance.igst_rate
                # Invalidate line item cache and recalculate
                cache_key_line = f"line_item:{line_item.id}:total"
                try:
                    redis_client.delete(cache_key_line)
                    logger.debug(f"Invalidated cache for LineItem: {cache_key_line}")
                except redis.RedisError as e:
                    logger.warning(f"Failed to invalidate cache for {cache_key_line}: {str(e)}")
                total_data = calculate_line_item_total(line_item)
                line_item.cgst_amount = total_data.get('cgst_amount', Decimal('0.00')).quantize(Decimal('0.01'))
                line_item.sgst_amount = total_data.get('sgst_amount', Decimal('0.00')).quantize(Decimal('0.01'))
                line_item.igst_amount = total_data.get('igst_amount', Decimal('0.00')).quantize(Decimal('0.01'))
                line_item.total_amount = total_data['total'].quantize(Decimal('0.01'))
                try:
                    line_item.save(user=user, skip_validation=True)
                    logger.info(f"Updated LineItem {line_item.id} for Invoice {instance.invoice_number} with new GST rates and totals")
                except Exception as e:
                    logger.error(f"Failed to update LineItem {line_item.id} for Invoice {instance.invoice_number}: {str(e)}", exc_info=True)
                    raise InvoiceValidationError(
                        message=f"Failed to update LineItem {line_item.id}: {str(e)}",
                        code="line_item_update_error",
                        details={"error": str(e)}
                    )

        # Update invoice totals based on line items
        total_data = calculate_total_amount(instance)
        instance.base_amount = total_data['base'].quantize(Decimal('0.01'))
        instance.cgst_amount = total_data['cgst'].quantize(Decimal('0.01'))
        instance.sgst_amount = total_data['sgst'].quantize(Decimal('0.01'))
        instance.igst_amount = total_data['igst'].quantize(Decimal('0.01'))
        instance.total_amount = total_data['total'].quantize(Decimal('0.01'))

        if user:
            if not instance.pk:
                instance.created_by = user
            instance.updated_by = user
        if commit:
            instance.save(user=user, skip_validation=False)
            logger.info(f"Invalidated cache for Invoice {instance.id}: {cache_key}")
        return instance
