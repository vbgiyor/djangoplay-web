import json
import logging
import zlib
from decimal import Decimal

from core.utils.redis_client import redis_client
from django import forms
from django.db import transaction

from invoices.constants import (
    DESCRIPTION_MAX_LENGTH,
    HSN_SAC_CODE_MAX_LENGTH,
)
from invoices.exceptions import GSTValidationError
from invoices.models.invoice import Invoice
from invoices.models.line_item import LineItem
from invoices.services.line_item import calculate_line_item_total

logger = logging.getLogger(__name__)

class LineItemForm(forms.ModelForm):

    """Form for creating and updating LineItem instances."""

    class Meta:
        model = LineItem
        fields = [
            'invoice', 'description', 'hsn_sac_code', 'quantity', 'unit_price',
            'discount', 'cgst_rate', 'sgst_rate', 'igst_rate', 'cgst_amount',
            'sgst_amount', 'igst_amount', 'total_amount'
        ]
        widgets = {
            'invoice': forms.Select(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
            }),
            'description': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': DESCRIPTION_MAX_LENGTH,
                'placeholder': 'Enter line item description',
            }),
            'hsn_sac_code': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'maxlength': HSN_SAC_CODE_MAX_LENGTH,
                'placeholder': 'Enter HSN/SAC code',
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter quantity',
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter unit price',
            }),
            'discount': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter discount',
            }),
            'cgst_rate': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter CGST rate',
                'readonly': True,
            }),
            'sgst_rate': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter SGST rate',
                'readonly': True,
            }),
            'igst_rate': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter IGST rate',
                'readonly': True,
            }),
            'cgst_amount': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0',
                'placeholder': 'CGST amount (calculated)',
                'readonly': True,
            }),
            'sgst_amount': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0',
                'placeholder': 'SGST amount (calculated)',
                'readonly': True,
            }),
            'igst_amount': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0',
                'placeholder': 'IGST amount (calculated)',
                'readonly': True,
            }),
            'total_amount': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-md focus:ring focus:ring-blue-300',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Total amount (calculated)',
                'readonly': True,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.debug(f"Initializing LineItemForm with fields: {self.Meta.fields}")

        if 'invoice' in self.fields:
            try:
                redis_conn = redis_client
                cached_list = redis_conn.get('invoices_search_list')
                if cached_list:
                    invoice_choices = json.loads(zlib.decompress(cached_list).decode())
                    self.fields['invoice'].choices = [(id_, num) for id_, num in invoice_choices]
                    logger.info(f"Fetched {len(invoice_choices)} invoice choices from Redis cache")
                else:
                    logger.warning("invoices_search_list not found in Redis, falling back to DB")
                    self.fields['invoice'].choices = [
                        (invoice.id, invoice.invoice_number)
                        for invoice in Invoice.all_objects.filter(
                            deleted_at__isnull=True, is_active=True
                        ).only('id', 'invoice_number')[:1000]
                    ]
            except Exception as e:
                logger.error(f"Failed to fetch invoice choices from Redis: {str(e)}", exc_info=True)
                self.fields['invoice'].choices = [
                    (invoice.id, invoice.invoice_number)
                    for invoice in Invoice.all_objects.filter(
                        deleted_at__isnull=True, is_active=True
                    ).only('id', 'invoice_number')[:1000]
                ]
                logger.warning("Fell back to database for invoice choices due to Redis error")


        # If editing an existing LineItem, refresh tax amounts and total_amount
        if self.instance and self.instance.pk:
            self.instance.refresh_from_db()
            total_data = calculate_line_item_total(self.instance)
            self.instance.cgst_amount = total_data.get('cgst_amount', Decimal('0.00')).quantize(Decimal('0.01'))
            self.instance.sgst_amount = total_data.get('sgst_amount', Decimal('0.00')).quantize(Decimal('0.01'))
            self.instance.igst_amount = total_data.get('igst_amount', Decimal('0.00')).quantize(Decimal('0.01'))
            self.instance.total_amount = total_data['total'].quantize(Decimal('0.01'))
            self.initial['cgst_amount'] = self.instance.cgst_amount
            self.initial['sgst_amount'] = self.instance.sgst_amount
            self.initial['igst_amount'] = self.instance.igst_amount
            self.initial['total_amount'] = self.instance.total_amount
            logger.debug(f"Refreshed LineItem {self.instance.id} with updated totals: {total_data}")

    def clean_hsn_sac_code(self):
        hsn_sac_code = self.cleaned_data.get('hsn_sac_code')
        if hsn_sac_code:
            from invoices.services.line_item import validate_hsn_sac
            try:
                validate_hsn_sac(hsn_sac_code)
            except Exception as e:
                raise forms.ValidationError(
                    f"Invalid HSN/SAC code: {str(e)}",
                    code="invalid_hsn_sac_code",
                    params={"value": hsn_sac_code}
                )
        return hsn_sac_code

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity <= 0:
            raise forms.ValidationError(
                "Quantity must be greater than zero.",
                code="invalid_quantity",
                params={"value": quantity}
            )
        return quantity

    def clean_unit_price(self):
        unit_price = self.cleaned_data.get('unit_price')
        if unit_price is not None and unit_price < 0:
            raise forms.ValidationError(
                "Unit price cannot be negative.",
                code="invalid_unit_price",
                params={"value": unit_price}
            )
        return unit_price

    def clean_discount(self):
        discount = self.cleaned_data.get('discount')
        if discount is not None and discount < 0:
            raise forms.ValidationError(
                "Discount cannot be negative.",
                code="invalid_discount",
                params={"value": discount}
            )
        return discount

    def clean(self):
        cleaned_data = super().clean()
        invoice = cleaned_data.get('invoice')
        cgst_rate = cleaned_data.get('cgst_rate')
        sgst_rate = cleaned_data.get('sgst_rate')
        igst_rate = cleaned_data.get('igst_rate')
        quantity = cleaned_data.get('quantity')
        unit_price = cleaned_data.get('unit_price')
        discount = cleaned_data.get('discount') or Decimal('0.00')
        hsn_sac_code = cleaned_data.get('hsn_sac_code')

        if invoice and invoice.billing_country and invoice.billing_country.country_code.upper() == 'IN':
            if invoice.tax_exemption_status not in ['EXEMPT', 'ZERO_RATED']:
                from invoices.services.gst_configuration import validate_gst_rates
                try:
                    validate_gst_rates(
                        cgst_rate=cgst_rate,
                        sgst_rate=sgst_rate,
                        igst_rate=igst_rate,
                        region_id=invoice.billing_region.id if invoice.billing_region else None,
                        country_id=invoice.billing_country.id,
                        issue_date=invoice.issue_date,
                        tax_exemption_status=invoice.tax_exemption_status,
                        hsn_sac_code=hsn_sac_code
                    )
                except GSTValidationError as e:
                    raise forms.ValidationError(
                        f"GST validation failed: {str(e)}",
                        code="gst_validation_error"
                    )

        # Validate total amount
        if quantity is not None and unit_price is not None:
            base_amount = (quantity * unit_price - discount).quantize(Decimal('0.01'))
            if base_amount < 0:
                raise forms.ValidationError(
                    "Base amount (quantity * unit_price - discount) cannot be negative.",
                    code="invalid_base_amount"
                )
            total_data = calculate_line_item_total(self.instance)
            calculated_total = total_data['total'].quantize(Decimal('0.01'))
            if cleaned_data.get('total_amount') != calculated_total:
                logger.warning(
                    f"Total amount mismatch for LineItem {self.instance.id or 'new'}: "
                    f"Form total={cleaned_data.get('total_amount')}, Calculated total={calculated_total}"
                )
                cleaned_data['total_amount'] = calculated_total
                cleaned_data['cgst_amount'] = total_data.get('cgst_amount', Decimal('0.00')).quantize(Decimal('0.01'))
                cleaned_data['sgst_amount'] = total_data.get('sgst_amount', Decimal('0.00')).quantize(Decimal('0.01'))
                cleaned_data['igst_amount'] = total_data.get('igst_amount', Decimal('0.00')).quantize(Decimal('0.01'))

        return cleaned_data

    @transaction.atomic
    def save(self, commit=True, user=None):
        logger.debug(f"Saving LineItemForm: {self.cleaned_data.get('description', 'New LineItem')}, user={user}")
        instance = super().save(commit=False)
        # Update tax amounts and totals
        total_data = calculate_line_item_total(instance)
        instance.cgst_amount = total_data.get('cgst_amount', Decimal('0.00')).quantize(Decimal('0.01'))
        instance.sgst_amount = total_data.get('sgst_amount', Decimal('0.00')).quantize(Decimal('0.01'))
        instance.igst_amount = total_data.get('igst_amount', Decimal('0.00')).quantize(Decimal('0.01'))
        instance.total_amount = total_data['total'].quantize(Decimal('0.01'))
        # Update audit fields
        if user:
            if not instance.pk:
                instance.created_by = user
            instance.updated_by = user
        if commit:
            instance.save(user=user, skip_validation=False)
            cache_key = f"line_item:{instance.id}:total"
            redis_client.delete(cache_key)
            logger.info(f"Saved LineItem {instance.id} and invalidated cache: {cache_key}")
        return instance
