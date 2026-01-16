import json
import logging
from decimal import Decimal

import redis
from core.utils.redis_client import redis_client
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Max, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from entities.models import Entity
from locations.models.custom_country import CustomCountry
from users.models import Member
from utilities.commons.decimal import get_safe_decimal

from invoices.exceptions import GSTValidationError, InvoiceValidationError
from invoices.services.gst_configuration import validate_gst_rates
from invoices.services.line_item import calculate_line_item_total

logger = logging.getLogger(__name__)

@transaction.atomic
def generate_invoice_number():
    """
    Generate a unique invoice number in format INV/YYYY-YY/MM/TTTT/XXXXXX.
    Uses a 6-digit sequence number and 4 digits of timestamp (milliseconds) before it to support higher invoice volumes.
    Leverages database for sequence tracking with Redis as an optimization, using INV/YYYY-YY/MM/ as the sequence key.
    """
    from invoices.models.invoice import Invoice

    # Calculate financial year, month prefix, and last 4 digits of timestamp
    now = timezone.now()
    year = now.year
    month = now.month
    timestamp = timezone.now().strftime('%y%m%d%H%M%S%f')[-4:] # Unique random number
    financial_year = f"{str(year)[2:]}" if month >= 4 else f"{year - 1}-{str(year)[2:]}"
    invoice_prefix = f"INV/{financial_year}/{month:02d}/{timestamp}/"
    # Prefix for sequence tracking excludes timestamp to allow sequence increment
    sequence_prefix = f"INV/{financial_year}/{month:02d}/"

    # Cache key for Redis (based on sequence_prefix)
    cache_key = f"invoice_number_sequence:{sequence_prefix}"

    # Attempt to get sequence from Redis
    try:
        sequence = redis_client.get(cache_key)
        sequence = int(sequence) + 1 if sequence else 1
    except (redis.RedisError, ValueError):
        logger.warning("Redis unavailable or invalid sequence, falling back to database")
        sequence = None

    # Fallback to database if Redis is unavailable or sequence is invalid
    if sequence is None:
        # Use a more efficient query to get the max sequence number
        max_sequence = Invoice.objects.filter(
            invoice_number__startswith=sequence_prefix,
            deleted_at__isnull=True,
            is_active=True
        ).aggregate(max_seq=Max('invoice_number'))['max_seq']

        if max_sequence:
            try:
                sequence = int(max_sequence.split('/')[-1]) + 1  # Extract sequence after timestamp
            except (ValueError, IndexError):
                logger.error(f"Invalid invoice number format in database: {max_sequence}")
                raise InvoiceValidationError("Invalid invoice number format in database")
        else:
            sequence = 1

    # Generate unique invoice number with extended attempts
    max_attempts = 500  # Increased to handle higher collision rates
    max_sequence = 999999  # 6-digit sequence supports up to 1M invoices per prefix
    initial_sequence = sequence

    for attempt in range(max_attempts):
        invoice_number = f"{invoice_prefix}{sequence:06d}"  # Include timestamp before sequence
        # Check if invoice number already exists
        if not Invoice.objects.filter(invoice_number=invoice_number, deleted_at__isnull=True).exists():
            # Attempt to update Redis cache
            try:
                redis_client.setex(cache_key, 24 * 3600, sequence)  # Cache for 24 hours
                logger.debug(f"Updated Redis cache for {cache_key} with sequence {sequence}")
            except redis.RedisError:
                logger.warning(f"Failed to update Redis cache for {cache_key}")

            logger.info(f"Generated invoice number: {invoice_number}")
            return invoice_number

        sequence += 1
        # Prevent infinite loops by capping sequence
        if sequence > max_sequence:
            sequence = 1  # Reset to 1 and retry
        if sequence == initial_sequence:
            # We've looped through all possible sequences
            logger.error(f"Exhausted all sequence numbers for prefix {sequence_prefix}")
            raise InvoiceValidationError(f"Could not generate unique invoice number for prefix {sequence_prefix} after {max_attempts} attempts")

        # Log a warning every 100 attempts
        if attempt % 100 == 0 and attempt > 0:
            logger.warning(f"Attempt {attempt}/{max_attempts} for invoice number with prefix {sequence_prefix}, sequence {sequence}")

    logger.error(f"Failed to generate unique invoice number for prefix {sequence_prefix} after {max_attempts} attempts")
    raise InvoiceValidationError(f"Could not generate unique invoice number after {max_attempts} attempts")

def calculate_total_amount(invoice):
    """Calculate total amount including taxes based on line items."""
    from invoices.models.invoice import Invoice
    logger.debug(f"Calculating total for Invoice {invoice.invoice_number}")
    try:
        if not isinstance(invoice, Invoice):
            raise InvoiceValidationError(
                message="Invalid invoice object.",
                code="invalid_invoice_object",
                details={"invoice_id": getattr(invoice, 'id', None)}
            )

        cache_key = f"invoice:{invoice.id}:total_amount"
        cached_valid = redis_client.get(cache_key)
        if not cached_valid:
            try:
                cached_total = redis_client.get(cache_key)
                if cached_total:
                    logger.debug(f"Cache hit for invoice {invoice.id} total")
                    cached_data = json.loads(cached_total)
                    return {key: Decimal(value) if isinstance(value, str) else value for key, value in cached_data.items()}
            except redis.RedisError as e:
                logger.warning(f"Redis cache miss for invoice {invoice.id}: {str(e)}")

        line_items = invoice.line_items.filter(is_active=True, deleted_at__isnull=True)
        if not line_items.exists():
            logger.error(f"No active line items found for invoice {invoice.id}")
            raise InvoiceValidationError(
                message="No Active Line Item",
                code="no_line_items",
                details={"invoice_id": invoice.id}
            )
        logger.debug(f"Found {line_items.count()} active line items for invoice {invoice.id}: {[getattr(li, 'description', 'Unknown') for li in line_items]}")

        total_data = {
            'base': Decimal('0.00'),
            'total': Decimal('0.00'),
            'cgst': Decimal('0.00'),
            'sgst': Decimal('0.00'),
            'igst': Decimal('0.00')
        }

        for line_item in line_items:
            logger.debug(f"Processing line item {line_item.id} for invoice {invoice.id}: {getattr(line_item, 'description', 'Unknown')}")
            line_total = calculate_line_item_total(line_item)
            base_amount = line_total.get('base', Decimal('0.00'))
            if base_amount == 0:
                logger.warning(f"Line item {line_item.id} has zero base amount, checking quantity and unit price: quantity={line_item.quantity}, unit_price={line_item.unit_price}, discount={line_item.discount}")
                base_amount = (get_safe_decimal(line_item.quantity) * get_safe_decimal(line_item.unit_price) - get_safe_decimal(line_item.discount)).quantize(Decimal('0.01'))

            # Use aggregates to compute sums without loading all instances
            aggregates = invoice.line_items.filter(deleted_at__isnull=True, is_active=True).aggregate(
                base=Coalesce(
                    Sum(
                        F('quantity') * F('unit_price') - Coalesce(F('discount'), Value(Decimal('0.00')))
                    ),
                    Value(Decimal('0.00'))
                ),
                cgst=Coalesce(Sum('cgst_amount'), Value(Decimal('0.00'))),
                sgst=Coalesce(Sum('sgst_amount'), Value(Decimal('0.00'))),
                igst=Coalesce(Sum('igst_amount'), Value(Decimal('0.00'))),
                total=Coalesce(Sum('total_amount'), Value(Decimal('0.00')))
            )

            total_data['base'] = aggregates['base'].quantize(Decimal('0.01'))
            total_data['cgst'] = aggregates['cgst'].quantize(Decimal('0.01'))
            total_data['sgst'] = aggregates['sgst'].quantize(Decimal('0.01'))
            total_data['igst'] = aggregates['igst'].quantize(Decimal('0.01'))
            total_data['total'] = aggregates['total'].quantize(Decimal('0.01'))

            logger.debug(f"Line item {line_item.id} totals: base={base_amount}, total={line_total.get('total', base_amount)}, cgst={line_total.get('cgst_amount')}, sgst={line_total.get('sgst_amount')}, igst={line_total.get('igst_amount')}")

        total_data_for_cache = {key: str(value) for key, value in total_data.items()}
        try:
            redis_client.setex(cache_key, 3600, json.dumps(total_data_for_cache))
        except redis.RedisError as e:
            logger.warning(f"Failed to cache invoice total: {str(e)}")

        logger.info(f"Calculated totals for invoice {invoice.invoice_number}: {total_data}")
        return total_data
    except Exception as e:
        logger.error(f"Failed to calculate total for invoice {invoice.invoice_number}: {str(e)}", exc_info=True)
        raise InvoiceValidationError(
            message="Failed to calculate invoice total.",
            code="total_calculation_failed",
            details={"error": str(e)}
        )


@transaction.atomic
def update_invoice_status(invoice, user=None):
    from invoices.models.invoice import Invoice
    from invoices.models.status import Status
    """Update invoice status based on payment status."""
    logger.debug(f"Updating status for invoice {invoice.invoice_number}")
    try:
        if not isinstance(invoice, Invoice):
            raise InvoiceValidationError(
                message="Invalid invoice object.",
                code="invalid_invoice_object",
                details={"invoice_id": getattr(invoice, 'id', None)}
            )
        if not invoice.is_active or invoice.deleted_at:
            raise InvoiceValidationError(
                message="Cannot update status of inactive or deleted invoice.",
                code="inactive_invoice",
                details={"invoice_id": invoice.id}
            )

        cache_key_payments = f"invoice:{invoice.id}:total_payments"
        try:
            cached_total = redis_client.get(cache_key_payments)
            if cached_total:
                # Decode bytes to string if necessary
                if isinstance(cached_total, bytes):
                    cached_total = cached_total.decode('utf-8')
                total_payments = Decimal(cached_total)
            else:
                total_payments = None
        except redis.RedisError as e:
            logger.warning(f"Redis cache miss for total payments: {str(e)}")
            total_payments = None

        if total_payments is None:
            total_payments = invoice.payments.filter(
                is_active=True,
                deleted_at__isnull=True,
                status='COMPLETED'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            try:
                redis_client.setex(cache_key_payments, 3600, str(total_payments))
            except redis.RedisError as e:
                logger.warning(f"Failed to cache total payments: {str(e)}")

        status_codes = {
            'PAID': total_payments >= invoice.total_amount,
            'PARTIALLY_PAID': 0 < total_payments < invoice.total_amount,
            'OVERDUE': invoice.due_date and invoice.due_date < timezone.now().date() and total_payments == 0,
            'SENT': total_payments == 0 and (not invoice.due_date or invoice.due_date >= timezone.now().date())
        }

        new_status_code = next((code for code, condition in status_codes.items() if condition), 'SENT')
        cache_key_status = f"status:{new_status_code}"
        new_status = None
        try:
            cached_status = redis_client.get(cache_key_status)
            if cached_status:
                cached_data = json.loads(cached_status)
                new_status = Status.objects.get(id=cached_data['id'], is_active=True, deleted_at__isnull=True)
        except redis.RedisError as e:
            logger.warning(f"Redis cache miss for status {new_status_code}: {str(e)}")
        except Status.DoesNotExist:
            logger.warning(f"Cached status {new_status_code} not found in database")

        if not new_status:
            new_status = Status.objects.get(code=new_status_code, is_active=True, deleted_at__isnull=True)
            try:
                redis_client.setex(cache_key_status, 3600, json.dumps({'id': new_status.id, 'code': new_status.code}))
            except redis.RedisError as e:
                logger.warning(f"Failed to cache status: {str(e)}")

        if invoice.status_id != new_status.id:
            # Validate GST rates for India invoices in critical statuses
            skip_validation = True
            if invoice.has_gst_required_fields and new_status_code in ['PAID', 'PARTIALLY_PAID', 'OVERDUE', 'SENT']:
                validate_gst_rates(
                    cgst_rate=invoice.cgst_rate,
                    sgst_rate=invoice.sgst_rate,
                    igst_rate=invoice.igst_rate,
                    region_id=invoice.billing_region.id if invoice.billing_region else None,
                    country_id=invoice.billing_country.id,
                    issue_date=invoice.issue_date,
                    tax_exemption_status=invoice.tax_exemption_status,
                    hsn_sac_code=None
                )
                skip_validation = False
            invoice.status = new_status
            invoice.save(user=user, skip_validation=skip_validation)
            logger.info(f"Updated invoice {invoice.invoice_number} status to {new_status.code}")
        else:
            logger.debug(f"No status change needed for invoice {invoice.invoice_number}")

        return True
    except Status.DoesNotExist:
        raise InvoiceValidationError(
            message="Required invoice status not found.",
            code="invalid_status",
            details={"status_code": new_status_code}
        )
    except Exception as e:
        logger.error(f"Failed to update status for invoice {invoice.invoice_number}: {str(e)}", exc_info=True)
        raise InvoiceValidationError(
            message=f"Failed to update invoice status: {str(e)}",
            code="invalid_status",
            details={"error": str(e)}
        )

@transaction.atomic
def validate_invoice(invoice, exclude_pk=None):
    from invoices.models.invoice import Invoice
    """Validate Invoice object."""
    logger.debug(f"Validating Invoice: {invoice.invoice_number}")

    try:
        if isinstance(invoice, Invoice) and not invoice._state.db:  # Skip for Swagger schema generation
            logger.debug("Skipping validation for schema generation")
            return True
        if not isinstance(invoice, Invoice):
            raise InvoiceValidationError(
                message="Invalid invoice object.",
                code="invalid_invoice_object",
                details={"invoice_id": getattr(invoice, 'id', None)}
            )

        # invoice.invoice_number = normalize_text(invoice.invoice_number)
        if not invoice.invoice_number:
            raise InvoiceValidationError(
                message="Invoice number cannot be empty.",
                code="missing_invoice_number",
                details={"field": "invoice_number"}
            )

        cache_key_number = f"invoice_number:{invoice.invoice_number}"
        try:
            cached_number = redis_client.get(cache_key_number)
            if cached_number and (not exclude_pk or int(cached_number) != exclude_pk):
                raise InvoiceValidationError(
                    message="Invoice number already exists.",
                    code="duplicate_invoice_number",
                    details={"field": "invoice_number", "value": invoice.invoice_number}
                )
        except redis.RedisError as e:
            logger.warning(f"Redis cache miss for invoice number: {str(e)}")

        if Invoice.objects.filter(invoice_number=invoice.invoice_number, deleted_at__isnull=True).exclude(pk=exclude_pk).exists():
            try:
                redis_client.setex(cache_key_number, 3600, str(invoice.id or 0))
            except redis.RedisError as e:
                logger.warning(f"Failed to cache invoice number: {str(e)}")
            raise InvoiceValidationError(
                message="Invoice number already exists.",
                code="duplicate_invoice_number",
                details={"field": "invoice_number", "value": invoice.invoice_number}
            )

        if not invoice.issuer or not invoice.issuer.is_active:
            raise InvoiceValidationError(
                message="Issuer must be active.",
                code="invalid_issuer",
                details={"field": "issuer", "issuer_id": getattr(invoice.issuer, 'id', None)}
            )

        if not invoice.recipient or not invoice.recipient.is_active:
            raise InvoiceValidationError(
                message="Recipient must be active.",
                code="invalid_recipient",
                details={"field": "recipient", "recipient_id": getattr(invoice.recipient, 'id', None)}
            )

        if not invoice.billing_address or not invoice.billing_address.is_active:
            raise InvoiceValidationError(
                message="Billing address must be active.",
                code="invalid_billing_address",
                details={"field": "billing_address", "address_id": getattr(invoice.billing_address, 'id', None)}
            )

        if not invoice.billing_country or not invoice.billing_country.is_active:
            raise InvoiceValidationError(
                message="Billing country must be active.",
                code="invalid_billing_country",
                details={"field": "billing_country", "country_id": getattr(invoice.billing_country, 'id', None)}
            )

        if invoice.billing_region and not invoice.billing_region.is_active:
            raise InvoiceValidationError(
                message="Billing region must be active.",
                code="invalid_billing_region",
                details={"field": "billing_region", "region_id": getattr(invoice.billing_region, 'id', None)}
            )

        if not invoice.issue_date:
            raise InvoiceValidationError(
                message="Issue date is required.",
                code="invalid_issue_date",
                details={"field": "issue_date"}
            )

        if invoice.due_date and invoice.due_date < invoice.issue_date:
            raise InvoiceValidationError(
                message="Due date cannot be before issue date.",
                code="invalid_due_date",
                details={"field": "due_date", "issue_date": invoice.issue_date}
            )

        if invoice.has_gst_required_fields:
            cache_key_gstin = f"gstin:{invoice.issuer_gstin}:{invoice.recipient_gstin}"
            try:
                cached_gstin = redis_client.get(cache_key_gstin)
                if cached_gstin:
                    return json.loads(cached_gstin)
            except redis.RedisError as e:
                logger.warning(f"Redis cache miss for GSTIN validation: {str(e)}")

            if invoice.issuer_gstin and invoice.recipient_gstin:
                is_inter_state = invoice.issuer_gstin[:2] != invoice.recipient_gstin[:2]
                if is_inter_state and invoice.billing_region and invoice.issuer_gstin[:2] == invoice.recipient_gstin[:2]:
                    raise GSTValidationError(
                        message="Inter-state invoice requires different issuer and recipient GSTIN state codes.",
                        code="invalid_gst_for_inter_state",
                        details={"issuer_gstin": invoice.issuer_gstin, "recipient_gstin": invoice.recipient_gstin}
                    )
                elif not is_inter_state and invoice.billing_region and invoice.issuer_gstin[:2] != invoice.billing_region.code:
                    raise GSTValidationError(
                        message="Issuer GSTIN state code must match billing region for intra-state invoice.",
                        code="issuer_gstin_state_mismatch",
                        details={"issuer_gstin": invoice.issuer_gstin, "region_code": invoice.billing_region.code}
                    )
                elif not is_inter_state and invoice.billing_region and invoice.recipient_gstin[:2] != invoice.billing_region.code:
                    raise GSTValidationError(
                        message="Recipient GSTIN state code must match billing region for intra-state invoice.",
                        code="recipient_gstin_state_mismatch",
                        details={"recipient_gstin": invoice.recipient_gstin, "region_code": invoice.billing_region.code}
                    )

                # Align with Entity: Validate issuer and recipient GSTIN against their default_address
                issuer = Entity.objects.filter(id=invoice.issuer_id, is_active=True).first()
                recipient = Entity.objects.filter(id=invoice.recipient_id, is_active=True).first()
                if issuer and issuer.default_address and issuer.default_address.city and issuer.default_address.city.subregion.region:
                    issuer_state_code = issuer.default_address.city.subregion.region.code
                    if invoice.issuer_gstin[:2] != issuer_state_code:
                        raise GSTValidationError(
                            message="Issuer GSTIN state code must match issuer's default address state.",
                            code="issuer_gstin_address_mismatch",
                            details={"issuer_gstin": invoice.issuer_gstin, "issuer_state": issuer_state_code}
                        )
                if recipient and recipient.default_address and recipient.default_address.city and recipient.default_address.city.subregion.region:
                    recipient_state_code = recipient.default_address.city.subregion.region.code
                    if invoice.recipient_gstin[:2] != recipient_state_code:
                        raise GSTValidationError(
                            message="Recipient GSTIN state code must match recipient's default address state.",
                            code="recipient_gstin_address_mismatch",
                            details={"recipient_gstin": invoice.recipient_gstin, "recipient_state": recipient_state_code}
                        )

            try:
                redis_client.setex(cache_key_gstin, 3600, json.dumps(True))
            except redis.RedisError as e:
                logger.warning(f"Failed to cache GSTIN validation: {str(e)}")

        logger.info(f"Validated Invoice: {invoice.invoice_number}")
        return True
    except Exception as e:
        logger.error(f"Failed to validate Invoice {invoice.invoice_number}: {str(e)}", exc_info=True)
        raise InvoiceValidationError(
            message=f"Failed to validate invoice: {str(e)}",
            code="invalid_fields",
            details={"error": str(e)}
        )
@transaction.atomic
def get_accessible_entities(user):
    """Retrieve accessible entities for a given user."""
    if isinstance(user, AnonymousUser):
        logger.debug("Anonymous user, returning empty set of accessible entities")
        return set()

    logger.debug(f"Fetching accessible entities for user {user.id}")
    try:
        cache_key = f"accessible_entities_{user.id}"
        try:
            cached_entities = redis_client.get(cache_key)
            if cached_entities:
                return set(json.loads(cached_entities))
        except redis.RedisError as e:
            logger.error(f"Redis cache miss for accessible entities: {str(e)}", exc_info=True)

        # Validate 'ACTV' status exists
        from invoices.models.status import Status
        if not Status.objects.filter(code='ACTV', is_active=True, deleted_at__isnull=True).exists():
            logger.error("No active 'ACTV' status found for Member model")
            raise InvoiceValidationError(
                message="No active 'ACTV' status found.",
                code="missing_status",
                details={"status_code": "ACTV"}
            )

        # Fetch entities where the user is a member via the Member model
        accessible_entities = set(Member.objects.filter(
            employee=user,
            status__code='ACTV',  # Only active members
            entity__is_active=True,
            entity__deleted_at__isnull=True
        ).values_list('entity_id', flat=True))

        try:
            redis_client.setex(cache_key, 172800, json.dumps(list(accessible_entities)))
        except redis.RedisError as e:
            logger.error(f"Failed to cache accessible entities: {str(e)}", exc_info=True)

        logger.info(f"Retrieved accessible entities for user {user.id}: {accessible_entities}")
        return accessible_entities
    except Exception as e:
        logger.error(f"Failed to fetch accessible entities for user {user.id}: {str(e)}", exc_info=True)
        raise InvoiceValidationError(
            message="Failed to fetch accessible entities.",
            code="accessible_entities_failed",
            details={"error": str(e)}
        )
@transaction.atomic
def get_remaining_amount(invoice):
    from invoices.models.invoice import Invoice
    """Calculate remaining amount for an invoice."""
    logger.debug(f"Calculating remaining amount for Invoice {invoice.invoice_number}")
    try:
        if not isinstance(invoice, Invoice):
            raise InvoiceValidationError(
                message="Invalid invoice object.",
                code="invalid_invoice_object",
                details={"invoice_id": getattr(invoice, 'id', None)}
            )

        cache_key = f"invoice:{invoice.id}:remaining_amount"
        try:
            cached_amount = redis_client.get(cache_key)
            if cached_amount:
                return Decimal(cached_amount)
        except redis.RedisError as e:
            logger.warning(f"Redis cache miss for remaining amount: {str(e)}")

        total_payments = Decimal('0.00')
        cache_key_payments = f"invoice:{invoice.id}:total_payments"
        try:
            cached_total = redis_client.get(cache_key_payments)
            if cached_total:
                total_payments = Decimal(cached_total)
            else:
                total_payments = invoice.payments.filter(
                    is_active=True,
                    deleted_at__isnull=True,
                    status='COMPLETED'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                redis_client.setex(cache_key_payments, 3600, str(total_payments))
        except redis.RedisError as e:
            logger.warning(f"Failed to cache total payments: {str(e)}")

        total_amount = calculate_total_amount(invoice)['total']
        remaining_amount = total_amount - total_payments

        try:
            redis_client.setex(cache_key, 3600, str(remaining_amount))
        except redis.RedisError as e:
            logger.warning(f"Failed to cache remaining amount: {str(e)}")

        logger.info(f"Calculated remaining amount for invoice {invoice.invoice_number}: {remaining_amount}")
        return remaining_amount
    except Exception as e:
        logger.error(f"Failed to calculate remaining amount for invoice {invoice.invoice_number}: {str(e)}", exc_info=True)
        raise InvoiceValidationError(
            message="Failed to calculate remaining amount.",
            code="remaining_amount_calculation_failed",
            details={"error": str(e)}
        )

def validate_currency(value):
    """Validate currency against active CustomCountry currency codes."""
    if value:
        valid_currencies = CustomCountry.objects.filter(
            is_active=True, deleted_at__isnull=True
        ).values_list('currency_code', flat=True).distinct()
        if value not in valid_currencies:
            raise ValidationError(
                f"Currency must be one of {list(valid_currencies)}.",
                code="invalid_currency"
            )

# def get_currency_choices():
#     """
#     Return currency choices from active CustomCountry currency codes.
#     Returns an empty list or default choices if the database is not ready.
#     """
#     try:
#         # Only query the database if it's accessible
#         return [
#             (code, code)
#             for code in CustomCountry.objects.filter(
#                 is_active=True, deleted_at__isnull=True
#             ).values_list('currency_code', flat=True).distinct()
#             if code
#         ]
#     except (ProgrammingError, OperationalError):
#         # Return a default or empty list during migrations or when DB is not ready
#         return [('INR', 'INR')]  # Fallback to Indian currency

def get_currency_choices():
    try:
        qs = CustomCountry.objects.filter(
            is_active=True, deleted_at__isnull=True
        ).values_list('currency_code', flat=True).distinct()
        return [(code, code) for code in qs if code]
    except Exception:
        # Database not ready during migrations / startup
        return [('INR', 'INR')]
