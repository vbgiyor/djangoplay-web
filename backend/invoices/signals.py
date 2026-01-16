import logging
from decimal import Decimal

import redis
from core.utils.redis_client import redis_client
from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver
from utilities.signals.disable_signals import disable_signals

from invoices.exceptions import GSTValidationError, InvoiceValidationError
from invoices.models.billing_schedule import BillingSchedule
from invoices.models.gst_configuration import GSTConfiguration
from invoices.models.invoice import Invoice
from invoices.models.line_item import LineItem
from invoices.models.payment import Payment
from invoices.models.payment_method import PaymentMethod
from invoices.models.status import Status
from invoices.services.invoice import calculate_total_amount, generate_invoice_number

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Invoice)
# def handle_invoice_pre_save(sender, instance, **kwargs):
#     logger.debug(f"Pre-save signal for Invoice: {instance.invoice_number or 'new'}, instance_id={id(instance)}")
#     User = get_user_model()
#     user = getattr(instance, 'created_by', None) or getattr(instance, 'updated_by', None)

#     if user and not isinstance(user, User):
#         logger.warning(f"Invalid user provided for Invoice {instance.invoice_number or 'new'}: {user}")
#         user = None

#     if not instance.pk:
#         if not instance.invoice_number:
#             instance.invoice_number = generate_invoice_number()
#             logger.debug(f"Generated invoice_number: {instance.invoice_number}")
#         if user:
#             instance.created_by = user
#     if user:
#         instance.updated_by = user

#     if not kwargs.get('skip_validation', False):
#         instance.clean()

@receiver(pre_save, sender=Invoice)
def handle_invoice_pre_save(sender, instance, **kwargs):
    logger.debug(f"Pre-save signal for Invoice: {instance.invoice_number or 'new'}, instance_id={id(instance)}")
    User = get_user_model()
    user = getattr(instance, 'created_by', None) or getattr(instance, 'updated_by', None)

    if user and not isinstance(user, User):
        logger.warning(f"Invalid user provided for Invoice {instance.invoice_number or 'new'}: {user}")
        user = None

    if not instance.pk:
        if not instance.invoice_number:
            instance.invoice_number = generate_invoice_number()
            logger.debug(f"Generated invoice_number: {instance.invoice_number}")
        if user:
            instance.created_by = user
    if user:
        instance.updated_by = user

    # Check skip_validation in instance attributes if not in kwargs
    skip_validation = kwargs.get('skip_validation', False) or getattr(instance, '_skip_validation', False)
    if not skip_validation:
        instance.clean()

@receiver(post_save, sender=Invoice)
def handle_invoice_post_save(sender, instance, created, **kwargs):
    logger.info(f"Post-save signal for Invoice: {instance.invoice_number}, created={created}")
    get_user_model()
    getattr(instance, 'created_by', None) or getattr(instance, 'updated_by', None)

    if created and not instance.status:
        cache_key = "status:default"
        default_status_id = redis_client.get(cache_key)
        if default_status_id:
            default_status_id = int(default_status_id)
        else:
            default_status_id = None
        if default_status_id is None:
            try:
                default_status = Status.objects.filter(
                    is_default=True, is_active=True, deleted_at__isnull=True
                ).first()
                if default_status:
                    try:
                        redis_client.setex(cache_key, 3600, str(default_status.id))
                    except redis.RedisError as e:
                        logger.warning(f"Failed to cache default status: {str(e)}")
                    with disable_signals(Invoice):
                        instance.status = default_status
                        instance.save(update_fields=['status'], skip_validation=True)
                    logger.debug(f"Set default status: {default_status.name}")
            except Exception as e:
                logger.error(f"Failed to set default status: {str(e)}", exc_info=True)

@receiver(pre_save, sender=LineItem)
def handle_line_item_pre_save(sender, instance, **kwargs):
    logger.debug(f"Pre-save signal for LineItem: {instance.description or 'new'}, instance_id={id(instance)}")
    User = get_user_model()
    user = getattr(instance, 'created_by', None) or getattr(instance, 'updated_by', None)

    if user and not isinstance(user, User):
        logger.warning(f"Invalid user provided for LineItem {instance.description or 'new'}: {user}")
        user = None

    if not instance.pk and user:
        instance.created_by = user
    if user:
        instance.updated_by = user

    if not kwargs.get('skip_validation', False):
        instance.clean()

@receiver(post_save, sender=LineItem)
def handle_line_item_post_save(sender, instance, created, **kwargs):
    logger.info(f"Post-save signal for LineItem: {instance.description}, created={created}")
    invoice = instance.invoice
    cache_key = f"invoice:{invoice.id}:total_amount"
    try:
        redis_client.delete(cache_key)
        total_data = calculate_total_amount(invoice)
        invoice.base_amount = total_data['base']
        invoice.total_amount = total_data['total']
        invoice.cgst_amount = total_data.get('cgst', Decimal('0.00'))
        invoice.sgst_amount = total_data.get('sgst', Decimal('0.00'))
        invoice.igst_amount = total_data.get('igst', Decimal('0.00'))
        with disable_signals(Invoice):
            instance.invoice.save(user=instance.updated_by, skip_validation=True)
        try:
            redis_client.setex(cache_key, 3600, str(invoice.total_amount))
        except redis.RedisError as e:
            logger.warning(f"Failed to cache invoice total_amount: {str(e)}")
        logger.debug(f"Updated invoice {invoice.invoice_number} total_amount after line item change")
    except redis.RedisError as e:
        logger.warning(f"Failed to handle cache for {cache_key}: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to update invoice {invoice.invoice_number} total_amount: {str(e)}", exc_info=True)
        raise InvoiceValidationError(
            message=f"Failed to update invoice total: {str(e)}",
            code="total_calculation_failed",
            details={"error": str(e)}
        )

@receiver(pre_save, sender=Status)
def handle_status_pre_save(sender, instance, **kwargs):
    logger.debug(f"Pre-save signal for Status: {instance.name or 'Unnamed'}, instance_id={id(instance)}")
    User = get_user_model()
    user = getattr(instance, 'created_by', None) or getattr(instance, 'updated_by', None)

    if user and not isinstance(user, User):
        logger.warning(f"Invalid user provided for Status {instance.name or 'Unnamed'}: {user}")
        user = None

    if not instance.pk and user:
        instance.created_by = user
    if user:
        instance.updated_by = user

    if not kwargs.get('skip_validation', False):
        instance.clean()

@receiver(post_save, sender=Status)
def handle_status_post_save(sender, instance, created, **kwargs):
    logger.info(f"Post-save signal for Status: {instance.name}, created={created}")
    try:
        redis_client.delete("status:default")
    except redis.RedisError as e:
        logger.warning(f"Failed to clear cache for status:default: {str(e)}")

@receiver(pre_save, sender=Payment)
def handle_payment_pre_save(sender, instance, **kwargs):
    logger.debug(f"Pre-save signal for Payment: {instance.payment_reference or 'new'}, instance_id={id(instance)}")
    User = get_user_model()
    user = getattr(instance, 'created_by', None) or getattr(instance, 'updated_by', None)

    if user and not isinstance(user, User):
        logger.warning(f"Invalid user provided for Payment {instance.payment_reference or 'new'}: {user}")
        user = None

    if not instance.pk and user:
        instance.created_by = user
    if user:
        instance.updated_by = user

    if not kwargs.get('skip_validation', False):
        instance.clean()

@receiver(post_save, sender=Payment)
def handle_payment_post_save(sender, instance, created, **kwargs):
    logger.info(f"Post-save signal for Payment: {instance.payment_reference or instance.id}, created={created}")
    invoice = instance.invoice
    cache_key = f"invoice:{invoice.id}:total_amount"
    try:
        redis_client.delete(cache_key)
        with disable_signals(Invoice):
            invoice.save(update_fields=['updated_at'], skip_validation=True)
        logger.debug(f"Updated invoice {invoice.invoice_number} updated_at after payment change")
    except redis.RedisError as e:
        logger.warning(f"Failed to clear cache for {cache_key}: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to update invoice {invoice.invoice_number} after payment: {str(e)}", exc_info=True)
        raise InvoiceValidationError(
            message=f"Failed to update invoice after payment: {str(e)}",
            code="save_error",
            details={"error": str(e)}
        )

@receiver(pre_save, sender=GSTConfiguration)
def handle_gst_configuration_pre_save(sender, instance, **kwargs):
    logger.debug(f"Pre-save signal for GSTConfiguration: {instance.description or instance.rate_type}, instance_id={id(instance)}")
    User = get_user_model()
    user = getattr(instance, 'created_by', None) or getattr(instance, 'updated_by', None)

    if user and not isinstance(user, User):
        logger.warning(f"Invalid user provided for GSTConfiguration {instance.description or instance.rate_type}: {user}")
        user = None

    if not instance.pk and user:
        instance.created_by = user
    if user:
        instance.updated_by = user

    # Respect the skip_validation flag
    if not kwargs.get('skip_validation', False):
        try:
            instance.clean()
        except GSTValidationError as e:
            logger.error(f"Validation failed for GSTConfiguration: {str(e)}", exc_info=True)
            raise
    else:
        logger.debug(f"Skipping validation for GSTConfiguration: {instance.description or instance.rate_type}")

@receiver(post_save, sender=GSTConfiguration)
def handle_gst_configuration_post_save(sender, instance, created, **kwargs):
    logger.info(f"Post-save signal for GSTConfiguration: {instance.description} ({instance.rate_type}), created={created}")

@receiver(pre_save, sender=BillingSchedule)
def handle_billing_schedule_pre_save(sender, instance, **kwargs):
    logger.debug(f"Pre-save signal for BillingSchedule: {instance.description or 'Unnamed'} - {instance.frequency}, instance_id={id(instance)}")
    User = get_user_model()
    user = getattr(instance, 'created_by', None) or getattr(instance, 'updated_by', None)

    if user and not isinstance(user, User):
        logger.warning(f"Invalid user provided for BillingSchedule {instance.description or 'Unnamed'}: {user}")
        user = None

    if not instance.pk and user:
        instance.created_by = user
    if user:
        instance.updated_by = user

    if not kwargs.get('skip_validation', False):
        try:
            instance.clean()
        except InvoiceValidationError as e:
            logger.error(f"Validation failed for BillingSchedule: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected validation error for BillingSchedule: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                message=f"Validation failed: {str(e)}",
                code="billing_schedule_validation_error",
                details={"error": str(e)}
            )

@receiver(post_save, sender=BillingSchedule)
def handle_billing_schedule_post_save(sender, instance, created, **kwargs):
    logger.info(f"Post-save signal for BillingSchedule: {instance.description} - {instance.frequency} (ID: {instance.id}), created={created}")
    if created:
        logger.info(f"BillingSchedule created: {instance} by user: {instance.created_by}")
    else:
        logger.info(f"BillingSchedule updated: {instance} by user: {instance.updated_by}")

@receiver(pre_save, sender=PaymentMethod)
def handle_payment_method_pre_save(sender, instance, **kwargs):
    logger.debug(f"Pre-save signal for PaymentMethod: {instance.code or 'new'}, instance_id={id(instance)}")
    User = get_user_model()
    user = getattr(instance, 'created_by', None) or getattr(instance, 'updated_by', None)

    if user and not isinstance(user, User):
        logger.warning(f"Invalid user provided for PaymentMethod {instance.code or 'new'}: {user}")
        user = None

    if not instance.pk and user:
        instance.created_by = user
    if user:
        instance.updated_by = user

    if not kwargs.get('skip_validation', False):
        instance.clean()

@receiver(post_save, sender=PaymentMethod)
def handle_payment_method_post_save(sender, instance, created, **kwargs):
    logger.info(f"Post-save signal for PaymentMethod: {instance.code}, created={created}")

@receiver(post_delete, sender=Invoice)
def log_invoice_soft_delete(sender, instance, **kwargs):
    if instance.deleted_at:
        logger.info(f"Invoice soft deleted: {instance.invoice_number} by user: {instance.deleted_by}")

@receiver(post_delete, sender=LineItem)
def log_line_item_soft_delete(sender, instance, **kwargs):
    if instance.deleted_at:
        logger.info(f"LineItem soft deleted: {instance.description} by user: {instance.deleted_by}")

@receiver(post_delete, sender=Status)
def log_status_soft_delete(sender, instance, **kwargs):
    if instance.deleted_at:
        logger.info(f"Status soft deleted: {instance.name} by user: {instance.deleted_by}")

@receiver(post_delete, sender=Payment)
def log_payment_soft_delete(sender, instance, **kwargs):
    if instance.deleted_at:
        logger.info(f"Payment soft deleted: {instance.payment_reference or instance.id} by user: {instance.deleted_by}")

@receiver(post_delete, sender=PaymentMethod)
def log_payment_method_soft_delete(sender, instance, **kwargs):
    if instance.deleted_at:
        logger.info(f"PaymentMethod soft deleted: {instance.code} by user: {instance.deleted_by}")

@receiver(post_delete, sender=GSTConfiguration)
def log_gst_configuration_soft_delete(sender, instance, **kwargs):
    if instance.deleted_at:
        logger.info(f"GSTConfiguration soft deleted: {instance.description} ({instance.rate_type}) by user: {instance.deleted_by}")

@receiver(post_delete, sender=BillingSchedule)
def log_billing_schedule_soft_delete(sender, instance, **kwargs):
    if instance.deleted_at:
        logger.info(f"BillingSchedule soft deleted: {instance.description} by user: {instance.deleted_by}")

@receiver(pre_delete, sender=Invoice)
def prevent_hard_delete_invoice(sender, instance, **kwargs):
    logger.warning(f"Attempted hard deletion of Invoice: {instance.invoice_number}")
    raise InvoiceValidationError(message="Cannot hard delete invoices; use soft deletion.", code="invoice_soft_delete_error")

@receiver(pre_delete, sender=LineItem)
def prevent_hard_delete_invoice_line_item(sender, instance, **kwargs):
    logger.warning(f"Attempted hard deletion of LineItem: {instance.description}")
    raise InvoiceValidationError(message="Cannot hard delete invoice line items; use soft deletion.", code="invoice_soft_delete_error")

@receiver(pre_delete, sender=Status)
def prevent_hard_delete_invoice_status(sender, instance, **kwargs):
    logger.warning(f"Attempted hard deletion of Status: {instance.name}")
    raise InvoiceValidationError(message="Cannot hard delete statuses; use soft deletion.", code="invoice_soft_delete_error")

@receiver(pre_delete, sender=PaymentMethod)
def prevent_hard_delete_payment_method(sender, instance, **kwargs):
    logger.warning(f"Attempted hard deletion of PaymentMethod: {instance.code}")
    raise InvoiceValidationError(message="Cannot hard delete payment methods; use soft deletion.", code="invoice_soft_delete_error")

@receiver(pre_delete, sender=Payment)
def prevent_hard_delete_invoice_payment(sender, instance, **kwargs):
    logger.warning(f"Attempted hard deletion of Payment: {instance.payment_reference}")
    raise InvoiceValidationError(message="Cannot hard delete payments; use soft deletion.", code="invoice_soft_delete_error")

@receiver(pre_delete, sender=GSTConfiguration)
def prevent_hard_delete_gst_configuration(sender, instance, **kwargs):
    logger.warning(f"Attempted hard deletion of GSTConfiguration: {instance.description} ({instance.rate_type})")
    raise GSTValidationError(message="Cannot hard delete GST configurations; use soft deletion.", code="invoice_soft_delete_error")

@receiver(pre_delete, sender=BillingSchedule)
def prevent_hard_delete_billing_schedule(sender, instance, **kwargs):
    logger.warning(f"Attempted hard deletion of BillingSchedule: {instance.description}")
    raise InvoiceValidationError(message="Cannot hard delete billing schedules; use soft deletion.", code="billing_schedule_validation_error")
