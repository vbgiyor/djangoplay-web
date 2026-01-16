import json
import logging
import re
from decimal import Decimal

import redis
from core.utils.redis_client import redis_client
from django.db import transaction
from utilities.commons.decimal import get_safe_decimal

from invoices.constants import DESCRIPTION_MAX_LENGTH, HSN_SAC_CODE_MAX_LENGTH, HSN_SAC_CODE_REGEX
from invoices.exceptions import GSTValidationError, InvoiceValidationError
from invoices.services.gst_configuration import fetch_gst_config, is_interstate_transaction, validate_gst_rates

logger = logging.getLogger(__name__)

@transaction.atomic
def validate_hsn_sac_code(hsn_sac_code: str = None) -> bool:
    """Validate HSN/SAC code format if provided."""
    logger.debug(f"Validating HSN/SAC code: {hsn_sac_code}")
    try:
        if hsn_sac_code is None:
            return True  # Allow None as per model

        cache_key = f"hsn_sac:{hsn_sac_code}"
        cached_valid = redis_client.get(cache_key)
        if cached_valid:
            return json.loads(cached_valid)

        if not isinstance(hsn_sac_code, str):
            raise GSTValidationError(
                message="HSN/SAC code must be a string.",
                code="invalid_hsn_sac_code",
                details={"field": "hsn_sac_code"}
            )
        if hsn_sac_code and len(hsn_sac_code) > HSN_SAC_CODE_MAX_LENGTH:
            raise GSTValidationError(
                message=f"HSN/SAC code cannot exceed {HSN_SAC_CODE_MAX_LENGTH} characters.",
                code="hsn_sac_code_too_long",
                details={"field": "hsn_sac_code", "value": hsn_sac_code}
            )
        if not re.match(HSN_SAC_CODE_REGEX, hsn_sac_code):
            raise GSTValidationError(
                message=f"HSN/SAC code must match pattern {HSN_SAC_CODE_REGEX}.",
                code="invalid_hsn_sac_code",
                details={"field": "hsn_sac_code", "value": hsn_sac_code}
            )

        try:
            redis_client.setex(cache_key, 3600, json.dumps(True))
        except redis.RedisError as e:
            logger.warning(f"Failed to cache HSN/SAC code: {str(e)}")

        logger.info(f"Validated HSN/SAC code: {hsn_sac_code}")
        return True
    except Exception as e:
        logger.error(f"Failed to validate HSN/SAC code {hsn_sac_code}: {str(e)}", exc_info=True)
        raise GSTValidationError(
            message=f"Failed to validate HSN/SAC code: {str(e)}",
            code="invalid_hsn_sac_code",
            details={"error": str(e)}
        )

@transaction.atomic
def calculate_line_item_total(line_item):
    """Calculate the total amount for a LineItem, including GST."""
    logger.debug(f"Calculating total for LineItem: {line_item.description}")
    from decimal import Decimal

    from invoices.models.line_item import LineItem

    try:
        if not isinstance(line_item, LineItem):
            raise InvoiceValidationError(
                message="Invalid line item object.",
                code="invalid_line_item",
                details={"line_item_id": getattr(line_item, 'id', None)}
            )

        cache_key = f"line_item:{line_item.id or 'new'}:total"
        # Invalidate cache to ensure fresh calculation with updated is_interstate_transaction logic
        try:
            redis_client.delete(cache_key)
            logger.debug(f"Invalidated cache for line item total: {cache_key}")
        except redis.RedisError as e:
            logger.warning(f"Failed to invalidate cache for {cache_key}: {str(e)}")

        try:
            cached_total = redis_client.get(cache_key)
            if cached_total:
                logger.debug(f"Cache hit for line item total: {cache_key}")
                cached_data = json.loads(cached_total)
                # Validate cached data against current line item attributes
                base_amount = (get_safe_decimal(line_item.quantity) * get_safe_decimal(line_item.unit_price) - get_safe_decimal(line_item.discount or 0)).quantize(Decimal('0.01'))
                expected_total = base_amount
                is_inter_state = is_interstate_transaction(
                    seller_gstin=line_item.invoice.issuer_gstin,
                    buyer_gstin=line_item.invoice.recipient_gstin,
                    billing_region_id=line_item.invoice.billing_region.id if line_item.invoice.billing_region else None,
                    billing_country_id=line_item.invoice.billing_country.id,
                    issuer=line_item.invoice.issuer,
                    recipient=line_item.invoice.recipient,
                    issue_date=line_item.invoice.issue_date
                )
                if line_item.invoice.tax_exemption_status not in ['EXEMPT', 'ZERO_RATED']:
                    if is_inter_state:
                        expected_total += (base_amount * get_safe_decimal(line_item.igst_rate) / Decimal('100')).quantize(Decimal('0.01'))
                    else:
                        expected_total += (base_amount * get_safe_decimal(line_item.cgst_rate) / Decimal('100')).quantize(Decimal('0.01'))
                        expected_total += (base_amount * get_safe_decimal(line_item.sgst_rate) / Decimal('100')).quantize(Decimal('0.01'))
                expected_total = expected_total.quantize(Decimal('0.01'))
                cached_total_value = Decimal(cached_data['total']).quantize(Decimal('0.01'))
                cached_attributes = {
                    'quantity': Decimal(cached_data.get('quantity', line_item.quantity)),
                    'unit_price': Decimal(cached_data.get('unit_price', line_item.unit_price)),
                    'discount': Decimal(cached_data.get('discount', line_item.discount or 0)),
                    'cgst_rate': Decimal(cached_data.get('cgst_rate', line_item.cgst_rate or 0)),
                    'sgst_rate': Decimal(cached_data.get('sgst_rate', line_item.sgst_rate or 0)),
                    'igst_rate': Decimal(cached_data.get('igst_rate', line_item.igst_rate or 0)),
                    'tax_exemption_status': cached_data.get('tax_exemption_status', line_item.invoice.tax_exemption_status)
                }
                current_attributes = {
                    'quantity': get_safe_decimal(line_item.quantity),
                    'unit_price': get_safe_decimal(line_item.unit_price),
                    'discount': get_safe_decimal(line_item.discount or 0),
                    'cgst_rate': get_safe_decimal(line_item.cgst_rate),
                    'sgst_rate': get_safe_decimal(line_item.sgst_rate),
                    'igst_rate': get_safe_decimal(line_item.igst_rate),
                    'tax_exemption_status': line_item.invoice.tax_exemption_status
                }
                if cached_attributes != current_attributes:
                    logger.warning(f"Invalidating cache for {cache_key} due to attribute mismatch")
                    redis_client.delete(cache_key)
                    cached_total = None
                elif cached_total_value == expected_total:
                    return {
                        'base': base_amount,
                        'total': cached_total_value,
                        'cgst_amount': Decimal(cached_data.get('cgst_amount', '0.00')).quantize(Decimal('0.01')),
                        'sgst_amount': Decimal(cached_data.get('sgst_amount', '0.00')).quantize(Decimal('0.01')),
                        'igst_amount': Decimal(cached_data.get('igst_amount', '0.00')).quantize(Decimal('0.01'))
                    }
                else:
                    logger.warning(f"Invalid cache for {cache_key}: cached {cached_total_value} != expected {expected_total}")
                    redis_client.delete(cache_key)
                    cached_total = None
        except redis.RedisError as e:
            logger.warning(f"Redis cache miss for line item total: {str(e)}")

        # Calculate base amount
        base_amount = (get_safe_decimal(line_item.quantity) * get_safe_decimal(line_item.unit_price) - get_safe_decimal(line_item.discount or 0)).quantize(Decimal('0.01'))
        if base_amount <= 0:
            raise InvoiceValidationError(
                message="Base amount must be positive.",
                code="invalid_base_amount",
                details={"quantity": str(line_item.quantity), "unit_price": str(line_item.unit_price), "discount": str(line_item.discount or 0)}
            )

        # Initialize total and tax amounts
        total = base_amount
        cgst_amount = Decimal('0.00')
        sgst_amount = Decimal('0.00')
        igst_amount = Decimal('0.00')

        # Apply GST if not exempt
        if line_item.invoice.billing_country.country_code.upper() == 'IN' and line_item.invoice.has_gst_required_fields and line_item.invoice.tax_exemption_status not in ['EXEMPT', 'ZERO_RATED']:
            is_inter_state = is_interstate_transaction(
                seller_gstin=line_item.invoice.issuer_gstin,
                buyer_gstin=line_item.invoice.recipient_gstin,
                billing_region_id=line_item.invoice.billing_region.id if line_item.invoice.billing_region else None,
                billing_country_id=line_item.invoice.billing_country.id,
                issuer=line_item.invoice.issuer,
                recipient=line_item.invoice.recipient,
                issue_date=line_item.invoice.issue_date
            )
            if is_inter_state:
                igst_amount = (base_amount * get_safe_decimal(line_item.igst_rate) / Decimal('100')).quantize(Decimal('0.01'))
                total += igst_amount
            else:
                cgst_amount = (base_amount * get_safe_decimal(line_item.cgst_rate) / Decimal('100')).quantize(Decimal('0.01'))
                sgst_amount = (base_amount * get_safe_decimal(line_item.sgst_rate) / Decimal('100')).quantize(Decimal('0.01'))
                total += cgst_amount + sgst_amount

        total_data = {
            'base': base_amount,
            'total': total.quantize(Decimal('0.01')),
            'cgst_amount': cgst_amount.quantize(Decimal('0.01')),
            'sgst_amount': sgst_amount.quantize(Decimal('0.01')),
            'igst_amount': igst_amount.quantize(Decimal('0.01')),
            'quantity': str(line_item.quantity),
            'unit_price': str(line_item.unit_price),
            'discount': str(line_item.discount or '0.00'),
            'cgst_rate': str(line_item.cgst_rate or '0.00'),
            'sgst_rate': str(line_item.sgst_rate or '0.00'),
            'igst_rate': str(line_item.igst_rate or '0.00'),
            'tax_exemption_status': line_item.invoice.tax_exemption_status
        }

        if total_data['total'] <= 0:
            raise InvoiceValidationError(
                message="Total amount must be positive.",
                code="invalid_total_amount",
                details={"field": "total_amount", "value": str(total_data['total'])}
            )

        # Convert Decimal to strings for JSON serialization
        serialized_total_data = {
            'base': str(total_data['base']),
            'total': str(total_data['total']),
            'cgst_amount': str(total_data['cgst_amount']),
            'sgst_amount': str(total_data['sgst_amount']),
            'igst_amount': str(total_data['igst_amount']),
            'quantity': str(total_data['quantity']),
            'unit_price': str(total_data['unit_price']),
            'discount': str(total_data['discount']),
            'cgst_rate': str(total_data['cgst_rate']),
            'sgst_rate': str(total_data['sgst_rate']),
            'igst_rate': str(total_data['igst_rate']),
            'tax_exemption_status': total_data['tax_exemption_status']
        }

        try:
            redis_client.setex(cache_key, 3600, json.dumps(serialized_total_data))
            logger.info(f"Cached line item total: {cache_key}")
        except redis.RedisError as e:
            logger.warning(f"Failed to cache line item total: {str(e)}")

        logger.info(f"Calculated total for LineItem {line_item.description}: {total_data}")
        return total_data
    except Exception as e:
        logger.error(f"Error calculating total for line item {line_item.description}: {str(e)}", exc_info=True)
        raise InvoiceValidationError(
            message=f"Failed to calculate line item total: {str(e)}",
            code="total_calculation_failed",
            details={"error": str(e)}
        )

@transaction.atomic
def validate_line_item(line_item, exclude_pk=None):
    """Validate a LineItem instance."""
    logger.debug(f"Validating LineItem: {line_item.description}, exclude_pk={exclude_pk}")
    from invoices.models.line_item import LineItem

    try:
        if not line_item.description or len(line_item.description) > DESCRIPTION_MAX_LENGTH:
            raise InvoiceValidationError(
                message=f"Description must be non-empty and not exceed {DESCRIPTION_MAX_LENGTH} characters.",
                code="invalid_description",
                details={"field": "description", "value": line_item.description}
            )

        # Validate HSN/SAC code
        if line_item.hsn_sac_code:
            validate_hsn_sac_code(line_item.hsn_sac_code)

        # Check uniqueness within invoice
        cache_key = f"line_item:invoice:{line_item.invoice_id}:description:{line_item.description}:hsn_sac:{line_item.hsn_sac_code or ''}"
        try:
            cached_id = redis_client.get(cache_key)
            if cached_id and (not exclude_pk or int(cached_id) != exclude_pk):
                raise InvoiceValidationError(
                    message="Line item description and HSN/SAC code must be unique within the invoice.",
                    code="duplicate_line_item_description",
                    details={"field": "description", "value": line_item.description, "hsn_sac_code": line_item.hsn_sac_code}
                )
        except redis.RedisError as e:
            logger.warning(f"Redis cache miss for line item uniqueness: {str(e)}")

        if LineItem.objects.filter(
            invoice=line_item.invoice,
            description=line_item.description,
            hsn_sac_code=line_item.hsn_sac_code,
            is_active=True,
            deleted_at__isnull=True
        ).exclude(pk=exclude_pk).exists():
            try:
                redis_client.setex(cache_key, 3600, str(line_item.id or 0))
            except redis.RedisError as e:
                logger.warning(f"Failed to cache line item uniqueness: {str(e)}")
            raise InvoiceValidationError(
                message="Line item description and HSN/SAC code must be unique within the invoice.",
                code="duplicate_line_item_description",
                details={"field": "description", "value": line_item.description, "hsn_sac_code": line_item.hsn_sac_code}
            )

        # Validate numeric fields
        quantity = get_safe_decimal(line_item.quantity)
        unit_price = get_safe_decimal(line_item.unit_price)
        discount = get_safe_decimal(line_item.discount or 0)

        if quantity <= 0:
            raise InvoiceValidationError(
                message="Quantity must be positive.",
                code="invalid_quantity",
                details={"field": "quantity", "value": str(line_item.quantity)}
            )
        if unit_price < 0:
            raise InvoiceValidationError(
                message="Unit price cannot be negative.",
                code="invalid_unit_price",
                details={"field": "unit_price", "value": str(line_item.unit_price)}
            )
        if discount < 0:
            raise InvoiceValidationError(
                message="Discount cannot be negative.",
                code="invalid_discount",
                details={"field": "discount", "value": str(line_item.discount)}
            )
        # Validate invoice
        if not line_item.invoice or not line_item.invoice.is_active:
            raise InvoiceValidationError(
                message="Line item must be associated with an active invoice.",
                code="invalid_invoice",
                details={"field": "invoice", "invoice_id": getattr(line_item.invoice, 'id', None)}
            )

        # Validate GST fields for India
        if line_item.invoice.has_gst_required_fields and line_item.invoice.billing_country.country_code.upper() == 'IN':
            if line_item.invoice.tax_exemption_status not in ['EXEMPT', 'ZERO_RATED'] and not line_item.hsn_sac_code:
                raise InvoiceValidationError(
                    message="HSN/SAC code is required for taxable items in India.",
                    code="missing_hsn_sac_code",
                    details={"field": "hsn_sac_code"}
                )

            # Validate GST rate consistency with invoice
            if line_item.invoice.tax_exemption_status == 'NONE':
                if line_item.cgst_rate != line_item.invoice.cgst_rate:
                    raise GSTValidationError(
                        message="CGST rate must match invoice CGST rate.",
                        code="inconsistent_gst_rates",
                        details={"field": "cgst_rate", "invoice_rate": str(line_item.invoice.cgst_rate)}
                    )
                if line_item.sgst_rate != line_item.invoice.sgst_rate:
                    raise GSTValidationError(
                        message="SGST rate must match invoice SGST rate.",
                        code="inconsistent_gst_rates",
                        details={"field": "sgst_rate", "invoice_rate": str(line_item.invoice.sgst_rate)}
                    )
                if line_item.igst_rate != line_item.invoice.igst_rate:
                    raise GSTValidationError(
                        message="IGST rate must match invoice IGST rate.",
                        code="inconsistent_gst_rates",
                        details={"field": "igst_rate", "invoice_rate": str(line_item.invoice.igst_rate)}
                    )

            # Fetch GST config to validate and set rates
            gst_config = fetch_gst_config(
                region_id=line_item.invoice.billing_region.id if line_item.invoice.billing_region else None,
                issue_date=line_item.invoice.issue_date,
                rate_type=line_item.invoice.tax_exemption_status if line_item.invoice.tax_exemption_status in ['EXEMPT', 'ZERO_RATED'] else 'STANDARD',
                exempt_zero_rated=line_item.invoice.tax_exemption_status in ['EXEMPT', 'ZERO_RATED']
            )

            # Set line item GST rates to match gst_config
            expected_cgst_rate = Decimal(gst_config['cgst_rate'])
            expected_sgst_rate = Decimal(gst_config['sgst_rate'])
            expected_igst_rate = Decimal(gst_config['igst_rate'])

            # Validate GST rate consistency with invoice
            if line_item.invoice.tax_exemption_status == 'NONE':
                if line_item.cgst_rate != line_item.invoice.cgst_rate:
                    logger.warning(f"Correcting CGST rate for line item {line_item.description}: {line_item.cgst_rate} -> {expected_cgst_rate}")
                    line_item.cgst_rate = expected_cgst_rate
                if line_item.sgst_rate != line_item.invoice.sgst_rate:
                    logger.warning(f"Correcting SGST rate for line item {line_item.description}: {line_item.sgst_rate} -> {expected_sgst_rate}")
                    line_item.sgst_rate = expected_sgst_rate
                if line_item.igst_rate != line_item.invoice.igst_rate:
                    logger.warning(f"Correcting IGST rate for line item {line_item.description}: {line_item.igst_rate} -> {expected_igst_rate}")
                    line_item.igst_rate = expected_igst_rate

            # Validate GST rates
            validate_gst_rates(
                cgst_rate=line_item.cgst_rate,
                sgst_rate=line_item.sgst_rate,
                igst_rate=line_item.igst_rate,
                region_id=line_item.invoice.billing_region.id if line_item.invoice.billing_region else None,
                country_id=line_item.invoice.billing_country.id,
                issue_date=line_item.invoice.issue_date,
                tax_exemption_status=line_item.invoice.tax_exemption_status,
                hsn_sac_code=line_item.hsn_sac_code
            )

        # Calculate and validate total_amount
        total_data = calculate_line_item_total(line_item)
        # Apply discount after multiplying quantity and unit_price to match calculate_line_item_total
        base_amount = (get_safe_decimal(line_item.quantity) * get_safe_decimal(line_item.unit_price)).quantize(Decimal('0.01')) - get_safe_decimal(line_item.discount or 0).quantize(Decimal('0.01'))
        expected_total = base_amount
        if line_item.invoice.tax_exemption_status not in ['EXEMPT', 'ZERO_RATED']:
            is_inter_state = is_interstate_transaction(
                seller_gstin=line_item.invoice.issuer_gstin,
                buyer_gstin=line_item.invoice.recipient_gstin,
                billing_region_id=line_item.invoice.billing_region.id if line_item.invoice.billing_region else None,
                billing_country_id=line_item.invoice.billing_country.id,
                issuer=line_item.invoice.issuer,
                recipient=line_item.invoice.recipient,
                issue_date=line_item.invoice.issue_date
            )
            if is_inter_state:
                expected_total += (base_amount * get_safe_decimal(line_item.igst_rate) / Decimal('100')).quantize(Decimal('0.01'))
            else:
                expected_total += (base_amount * get_safe_decimal(line_item.cgst_rate) / Decimal('100')).quantize(Decimal('0.01'))
                expected_total += (base_amount * get_safe_decimal(line_item.sgst_rate) / Decimal('100')).quantize(Decimal('0.01'))
        expected_total = expected_total.quantize(Decimal('0.01'))
        if total_data['total'] != expected_total:
            raise InvoiceValidationError(
                message=f"Total amount {total_data['total']} does not match expected {expected_total}.",
                code="invalid_total_amount",
                details={"calculated_total": str(total_data['total']), "expected_total": str(expected_total)}
            )

        logger.info(f"Validated LineItem: {line_item.description}")
    except (InvoiceValidationError, GSTValidationError) as e:
        logger.error(f"Validation error for line item {line_item.description}: {str(e)}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Error validating line item {line_item.description}: {str(e)}", exc_info=True)
        raise InvoiceValidationError(
            message=f"Failed to validate line item: {str(e)}",
            code="line_item_validation_error",
            details={"error": str(e)}
        )
