import json
import logging
from decimal import Decimal

import redis
from core.utils.redis_client import redis_client
from django.db import transaction
from django.utils import timezone
from entities.models import Entity

from invoices.constants import BILLING_FREQUENCY_CHOICES, BILLING_STATUS_CODES, DESCRIPTION_MAX_LENGTH
from invoices.exceptions import InvoiceValidationError
from invoices.services.invoice import calculate_total_amount, generate_invoice_number

logger = logging.getLogger(__name__)

@transaction.atomic
def validate_billing_schedule(schedule, exclude_pk=None):
    """Validate the BillingSchedule object."""
    from invoices.models.billing_schedule import BillingSchedule
    logger.debug(f"Validating BillingSchedule: {schedule.description or 'Unnamed'}")
    try:
        if not isinstance(schedule, BillingSchedule):
            raise InvoiceValidationError(
                message="Invalid billing schedule object.",
                code="invalid_billing_schedule",
                details={"schedule_id": getattr(schedule, 'id', None)}
            )

        if not isinstance(schedule.amount, Decimal):
            raise InvoiceValidationError(
                message="Billing amount must be a Decimal value.",
                code="invalid_billing_amount",
                details={"field": "amount", "type": type(schedule.amount).__name__}
            )

        # Allow zero amount for PAID invoices, require positive for others
        if schedule.amount is None:
            raise InvoiceValidationError(
                message="Billing amount cannot be null.",
                code="invalid_billing_amount",
                details={"field": "amount", "value": None}
            )
        invoice = getattr(schedule, 'invoice', None)  # Check if schedule is linked to an invoice
        if invoice and invoice.status.code == 'PAID':
            if schedule.amount < 0:
                raise InvoiceValidationError(
                    message="Billing amount cannot be negative for PAID invoices.",
                    code="invalid_billing_amount",
                    details={"field": "amount", "value": str(schedule.amount)}
                )
        else:
            if schedule.amount <= 0:
                raise InvoiceValidationError(
                    message="Billing amount must be positive for non-PAID invoices.",
                    code="invalid_billing_amount",
                    details={"field": "amount", "value": str(schedule.amount)}
                )

        if not schedule.entity or not Entity.objects.filter(id=schedule.entity.id, is_active=True).exists():
            raise InvoiceValidationError(
                message="Entity does not exist or is inactive.",
                code="inactive_entity",
                details={"field": "entity", "entity_id": schedule.entity.id if schedule.entity else None}
            )

        if not schedule.description or not schedule.description.strip():
            raise InvoiceValidationError(
                message="Description is required.",
                code="invalid_description",
                details={"field": "description"}
            )

        if len(schedule.description) > DESCRIPTION_MAX_LENGTH:
            raise InvoiceValidationError(
                message=f"Description cannot exceed {DESCRIPTION_MAX_LENGTH} characters.",
                code="invalid_description",
                details={"field": "description", "value": schedule.description}
            )

        if schedule.frequency not in dict(BILLING_FREQUENCY_CHOICES):
            raise InvoiceValidationError(
                message=f"Frequency must be one of {list(dict(BILLING_FREQUENCY_CHOICES).keys())}.",
                code="invalid_frequency",
                details={"field": "frequency", "value": schedule.frequency}
            )

        if schedule.status not in dict(BILLING_STATUS_CODES):
            raise InvoiceValidationError(
                message=f"Status must be one of {list(dict(BILLING_STATUS_CODES).keys())}.",
                code="invalid_billing_status",
                details={"field": "status", "value": schedule.status}
            )

        if schedule.status == 'COMPLETED' and not schedule.end_date:
            raise InvoiceValidationError(
                message="Completed billing schedules must have an end date.",
                code="invalid_billing_status",
                details={"field": "status", "value": schedule.status}
            )

        if schedule.end_date and schedule.end_date < schedule.start_date:
            raise InvoiceValidationError(
                message="End date cannot be before start date.",
                code="invalid_end_date",
                details={"field": "end_date", "start_date": schedule.start_date, "end_date": schedule.end_date}
            )

        if schedule.next_billing_date < schedule.start_date:
            raise InvoiceValidationError(
                message="Next billing date cannot be before start date.",
                code="invalid_next_billing_date",
                details={"field": "next_billing_date", "start_date": schedule.start_date, "next_billing_date": schedule.next_billing_date}
            )

        if schedule.end_date and schedule.next_billing_date > schedule.end_date:
            raise InvoiceValidationError(
                message="Next billing date cannot be after end date.",
                code="invalid_next_billing_date",
                details={"field": "next_billing_date", "end_date": schedule.end_date, "next_billing_date": schedule.next_billing_date}
            )

        cache_key = f"billing_schedule:entity:{schedule.entity.id}:description:{schedule.description}:start_date:{schedule.start_date.strftime('%Y%m%d')}"
        try:
            cached_unique = redis_client.get(cache_key)
            if cached_unique and (not exclude_pk or int(cached_unique) != exclude_pk):
                raise InvoiceValidationError(
                    message="A billing schedule with this entity, description, and start date already exists.",
                    code="duplicate_billing_schedule",
                    details={"fields": ["entity", "description", "start_date"]}
                )
        except Exception as e:
            logger.warning(f"Redis cache miss for billing schedule uniqueness: {str(e)}")
            # Fallback to database check if Redis fails
            if BillingSchedule.objects.filter(
                entity=schedule.entity,
                description=schedule.description,
                start_date=schedule.start_date,
                is_active=True
            ).exclude(pk=exclude_pk).exists():
                raise InvoiceValidationError(
                    message="A billing schedule with this entity, description, and start date already exists.",
                    code="duplicate_billing_schedule",
                    details={"fields": ["entity", "description", "start_date"]}
                )

        logger.info(f"Validated BillingSchedule: {schedule.description}")
        return True
    except Exception as e:
        logger.error(f"Failed to validate BillingSchedule {schedule.description or 'Unnamed'}: {str(e)}", exc_info=True)
        raise InvoiceValidationError(
            message=f"Failed to validate billing schedule: {str(e)}",
            code="billing_schedule_validation_error",
            details={"error": str(e)}
        )

@transaction.atomic
def cache_billing_schedule(schedule):
    """Cache the billing schedule in Redis after a successful save."""
    try:
        cache_key = f"billing_schedule:entity:{schedule.entity.id}:description:{schedule.description}:start_date:{schedule.start_date.strftime('%Y%m%d')}"
        redis_client.setex(cache_key, 3600, str(schedule.id))
        logger.debug(f"Cached billing schedule: {schedule.description} (ID: {schedule.id})")
    except redis.RedisError as e:
        logger.warning(f"Failed to cache billing schedule {schedule.description}: {str(e)}")

# @transaction.atomic
# def generate_invoices_from_billing_schedules(user=None):
#     """Generate invoices for active billing schedules with next_billing_date <= today."""
#     from invoices.models.billing_schedule import BillingSchedule
#     from invoices.models.invoice import Invoice
#     from invoices.models.status import Status
#     logger.debug("Starting invoice generation from billing schedules")
#     try:
#         today = timezone.now().date()
#         cache_key_run = f"billing_schedule:run:{today.strftime('%Y%m%d')}"
#         try:
#             if redis_client.get(cache_key_run):
#                 logger.info("Invoice generation already processed for today")
#                 return
#         except Exception as e:
#             logger.warning(f"Redis cache miss for invoice generation run: {str(e)}")
#             raise InvoiceValidationError(
#                 message="Failed to access cache for invoice generation.",
#                 code="redis_connection_error",
#                 details={"error": str(e)}
#             )

#         schedules = BillingSchedule.objects.filter(
#             is_active=True,
#             status='ACTIVE',
#             next_billing_date__lte=today
#         ).select_related("entity", "entity__billing_region", "entity__billing_country")

#         processed_schedules = 0
#         for schedule in schedules:
#             try:
#                 cache_key = f"billing_schedule:invoice:{schedule.id}:{today.strftime('%Y%m%d')}"
#                 try:
#                     if redis_client.get(cache_key):
#                         logger.debug(f"Invoice already generated for schedule {schedule.id} today")
#                         continue
#                 except Exception as e:
#                     logger.warning(f"Redis cache miss for schedule {schedule.id}: {str(e)}")
#                     raise InvoiceValidationError(
#                         message="Failed to access cache for invoice generation.",
#                         code="redis_connection_error",
#                         details={"error": str(e)}
#                     )

#                 validate_billing_schedule(schedule, exclude_pk=schedule.id)

#                 # Determine currency from entity's billing country
#                 currency = (
#                     schedule.entity.billing_country.currency_code
#                     if schedule.entity.billing_country and schedule.entity.billing_country.currency_code
#                     else "INR"  # Default to INR if not specified
#                 )

#                 # Determine tax exemption status
#                 tax_exemption_status = (
#                     "NONE"
#                     if schedule.entity.billing_country and schedule.entity.billing_country.country_code.upper() == "IN"
#                     and schedule.entity.billing_country.has_gst_required_fields
#                     else "EXEMPT"
#                 )

#                 invoice = Invoice(
#                     issuer=schedule.entity,
#                     recipient=schedule.entity,
#                     billing_address=schedule.entity.billing_address,
#                     billing_country=schedule.entity.billing_country,
#                     billing_region=schedule.entity.billing_region,
#                     issue_date=today,
#                     due_date=today + timezone.timedelta(days=30),
#                     currency=currency,
#                     base_amount=schedule.amount,
#                     tax_exemption_status=tax_exemption_status,
#                     status=Status.objects.get(code="DRAFT", is_active=True, deleted_at__isnull=True),
#                     created_by=user,
#                     updated_by=user,
#                     description=f"Invoice for {schedule.description}"[:DESCRIPTION_MAX_LENGTH]
#                 )
#                 invoice.invoice_number = generate_invoice_number()
#                 total_amount = calculate_total_amount(invoice)
#                 invoice.total_amount = total_amount
#                 invoice.save()

#                 cache_billing_schedule(schedule)  # Cache after successful save

#                 # Update next_billing_date based on frequency
#                 if schedule.frequency == "DAILY":
#                     schedule.next_billing_date += timezone.timedelta(days=1)
#                 elif schedule.frequency == "WEEKLY":
#                     schedule.next_billing_date += timezone.timedelta(days=7)
#                 elif schedule.frequency == "MONTHLY":
#                     schedule.next_billing_date += timezone.timedelta(days=30)
#                 elif schedule.frequency == "QUARTERLY":
#                     schedule.next_billing_date += timezone.timedelta(days=90)
#                 elif schedule.frequency == "YEARLY":
#                     schedule.next_billing_date += timezone.timedelta(days=365)

#                 if schedule.end_date and schedule.next_billing_date > schedule.end_date:
#                     schedule.status = "COMPLETED"
#                     schedule.is_active = False

#                 schedule.save()

#                 try:
#                     redis_client.setex(cache_key, 3600, str(invoice.id))
#                 except Exception as e:
#                     logger.warning(f"Failed to cache invoice for schedule {schedule.id}: {str(e)}")

#                 logger.info(f"Generated invoice {invoice.invoice_number} for billing schedule {schedule.description}")
#                 processed_schedules += 1
#             except Exception as e:
#                 logger.error(f"Failed to process schedule {schedule.id}: {str(e)}", exc_info=True)
#                 raise InvoiceValidationError(
#                     message=f"Failed to generate invoice for schedule {schedule.description}: {str(e)}",
#                     code="invoice_generation_failed",
#                     details={"schedule_id": schedule.id, "error": str(e)}
#                 )

#         try:
#             redis_client.setex(cache_key_run, 3600, json.dumps({"processed": processed_schedules}))
#         except Exception as e:
#             logger.warning(f"Failed to cache invoice generation run: {str(e)}")

#         logger.info(f"Processed {processed_schedules} billing schedules")
#     except Exception as e:
#         logger.error(f"Failed to generate invoices from billing schedules: {str(e)}", exc_info=True)
#         raise InvoiceValidationError(
#             message=f"Failed to generate invoices: {str(e)}",
#             code="invoice_generation_failed",
#             details={"error": str(e)}
#         )

@transaction.atomic
def generate_invoices_from_billing_schedules(user=None):
    """Generate invoices for active billing schedules with next_billing_date <= today."""
    from invoices.models.billing_schedule import BillingSchedule
    from invoices.models.invoice import Invoice
    from invoices.models.status import Status
    logger.debug("Starting invoice generation from billing schedules")
    try:
        today = timezone.now().date()
        cache_key_run = f"billing_schedule:run:{today.strftime('%Y%m%d')}"
        try:
            if redis_client.get(cache_key_run):
                logger.info("Invoice generation already processed for today")
                return
        except Exception as e:
            logger.warning(f"Redis cache miss for invoice generation run: {str(e)}")
            raise InvoiceValidationError(
                message="Failed to access cache for invoice generation.",
                code="redis_connection_error",
                details={"error": str(e)}
            )

        schedules = BillingSchedule.objects.filter(
            is_active=True,
            status='ACTIVE',
            next_billing_date__lte=today
        ).select_related("entity", "entity__billing_region", "entity__billing_country")

        processed_schedules = 0
        for schedule in schedules:
            try:
                cache_key = f"billing_schedule:invoice:{schedule.id}:{today.strftime('%Y%m%d')}"
                try:
                    if redis_client.get(cache_key):
                        logger.debug(f"Invoice already generated for schedule {schedule.id} today")
                        continue
                except Exception as e:
                    logger.warning(f"Redis cache miss for schedule {schedule.id}: {str(e)}")
                    raise InvoiceValidationError(
                        message="Failed to access cache for invoice generation.",
                        code="redis_connection_error",
                        details={"error": str(e)}
                    )

                validate_billing_schedule(schedule, exclude_pk=schedule.id)

                # Determine currency from entity's billing country
                currency = (
                    schedule.entity.billing_country.currency_code
                    if schedule.entity.billing_country and schedule.entity.billing_country.currency_code
                    else "INR"  # Default to INR if not specified
                )

                # Determine tax exemption status
                tax_exemption_status = (
                    "NONE"
                    if schedule.entity.billing_country and schedule.entity.billing_country.country_code.upper() == "IN"
                    and schedule.entity.billing_country.has_gst_required_fields
                    else "EXEMPT"
                )

                # Ensure billing_address belongs to recipient
                if not schedule.entity.billing_address or schedule.entity.billing_address.entity_mapping != schedule.entity.get_entity_mapping():
                    logger.warning(f"Billing address {schedule.entity.billing_address} does not match recipient {schedule.entity} entity mapping")
                    # Fallback to a valid address for the recipient
                    valid_address = schedule.entity.addresses.filter(
                        entity_mapping=schedule.entity.get_entity_mapping(),
                        is_active=True,
                        deleted_at__isnull=True
                    ).first()
                    if not valid_address:
                        raise InvoiceValidationError(
                            message="No valid billing address found for recipient entity.",
                            code="invalid_billing_address",
                            details={"entity_id": schedule.entity.id}
                        )
                    billing_address = valid_address
                else:
                    billing_address = schedule.entity.billing_address

                invoice = Invoice(
                    issuer=schedule.entity,
                    recipient=schedule.entity,
                    billing_address=billing_address,  # Use validated address
                    billing_country=schedule.entity.billing_country,
                    billing_region=schedule.entity.billing_region,
                    issue_date=today,
                    due_date=today + timezone.timedelta(days=30),
                    currency=currency,
                    base_amount=schedule.amount,
                    tax_exemption_status=tax_exemption_status,
                    status=Status.objects.get(code="DRAFT", is_active=True, deleted_at__isnull=True),
                    created_by=user,
                    updated_by=user,
                    description=f"Invoice for {schedule.description}"[:DESCRIPTION_MAX_LENGTH]
                )
                invoice.invoice_number = generate_invoice_number()
                total_amount = calculate_total_amount(invoice)
                invoice.total_amount = total_amount
                invoice.save(user=user, skip_validation=True)  # Explicitly skip validation

                cache_billing_schedule(schedule)  # Cache after successful save

                # Update next_billing_date based on frequency
                if schedule.frequency == "DAILY":
                    schedule.next_billing_date += timezone.timedelta(days=1)
                elif schedule.frequency == "WEEKLY":
                    schedule.next_billing_date += timezone.timedelta(days=7)
                elif schedule.frequency == "MONTHLY":
                    schedule.next_billing_date += timezone.timedelta(days=30)
                elif schedule.frequency == "QUARTERLY":
                    schedule.next_billing_date += timezone.timedelta(days=90)
                elif schedule.frequency == "YEARLY":
                    schedule.next_billing_date += timezone.timedelta(days=365)

                if schedule.end_date and schedule.next_billing_date > schedule.end_date:
                    schedule.status = "COMPLETED"
                    schedule.is_active = False

                schedule.save()

                try:
                    redis_client.setex(cache_key, 3600, str(invoice.id))
                except Exception as e:
                    logger.warning(f"Failed to cache invoice for schedule {schedule.id}: {str(e)}")

                logger.info(f"Generated invoice {invoice.invoice_number} for billing schedule {schedule.description}")
                processed_schedules += 1
            except Exception as e:
                logger.error(f"Failed to process schedule {schedule.id}: {str(e)}", exc_info=True)
                raise InvoiceValidationError(
                    message=f"Failed to generate invoice for schedule {schedule.description}: {str(e)}",
                    code="invoice_generation_failed",
                    details={"schedule_id": schedule.id, "error": str(e)}
                )

        try:
            redis_client.setex(cache_key_run, 3600, json.dumps({"processed": processed_schedules}))
        except Exception as e:
            logger.warning(f"Failed to cache invoice generation run: {str(e)}")

        logger.info(f"Processed {processed_schedules} billing schedules")
    except Exception as e:
        logger.error(f"Failed to generate invoices from billing schedules: {str(e)}", exc_info=True)
        raise InvoiceValidationError(
            message=f"Failed to generate invoices: {str(e)}",
            code="invoice_generation_failed",
            details={"error": str(e)}
        )
