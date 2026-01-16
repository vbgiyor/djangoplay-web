import json
import logging
import re
from decimal import Decimal, InvalidOperation

import redis
from core.utils.redis_client import redis_client
from django.db import transaction
from django.db.models import Sum

from invoices.constants import DESCRIPTION_MAX_LENGTH, PAYMENT_METHOD_CODE_MAX_LENGTH, PAYMENT_METHOD_NAME_MAX_LENGTH, PAYMENT_REFERENCE_MAX_LENGTH
from invoices.exceptions import InvoiceValidationError
from invoices.services.invoice import calculate_total_amount

logger = logging.getLogger(__name__)

@transaction.atomic
def validate_payment_amount(amount, invoice, payment_id=None):
    from invoices.models.invoice import Invoice
    """Validate payment amount against invoice total and existing payments."""
    logger.debug(f"Validating payment amount for invoice {invoice.invoice_number}")
    try:
        if not isinstance(invoice, Invoice) or not Invoice.objects.filter(id=invoice.id, is_active=True).exists():
            raise InvoiceValidationError(
                message="Invoice does not exist or is inactive.",
                code="invalid_invoice",
                details={"field": "invoice", "invoice_id": invoice.id if hasattr(invoice, 'id') else None}
            )

        if amount is None:
            raise InvoiceValidationError(
                message="Payment amount cannot be None.",
                code="invalid_payment_amount",
                details={"field": "amount", "value": None}
            )

        if isinstance(amount, str):
            try:
                amount = Decimal(amount)
            except InvalidOperation:
                raise InvoiceValidationError(
                    message=f"Invalid payment amount format: {amount}",
                    code="invalid_payment_amount_format",
                    details={"field": "amount", "value": amount}
                )
        elif not isinstance(amount, Decimal):
            raise InvoiceValidationError(
                message=f"Expected Decimal type for amount, got {type(amount)}.",
                code="invalid_payment_amount",
                details={"field": "amount", "value": str(amount)}
            )

        if amount <= 0:
            raise InvoiceValidationError(
                message="Payment amount must be positive.",
                code="invalid_payment_amount",
                details={"field": "amount", "value": str(amount)}
            )

        if not invoice.is_active:
            raise InvoiceValidationError(
                message="Cannot add payment to an inactive invoice.",
                code="inactive_invoice",
                details={"field": "invoice", "invoice_id": invoice.id}
            )

        cache_key = f"payment:amount:invoice:{invoice.id}:{str(amount)}:{payment_id or 'none'}"
        try:
            cached_valid = redis_client.get(cache_key)
            if cached_valid:
                return json.loads(cached_valid)
        except redis.RedisError as e:
            logger.warning(f"Redis cache miss for payment amount {amount}: {str(e)}")

        total_data = calculate_total_amount(invoice)
        total_amount = total_data['total']
        if total_amount < 0:
            raise InvoiceValidationError(
                message="Invoice total amount cannot be negative.",
                code="invalid_total_amount",
                details={"field": "total_amount", "value": str(total_amount)}
            )

        total_paid = invoice.payments.filter(is_active=True, status='COMPLETED').exclude(pk=payment_id).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        remaining = total_amount - total_paid
        if amount > remaining:
            raise InvoiceValidationError(
                message=f"Payment amount {amount} exceeds remaining invoice amount {remaining}.",
                code="excessive_payment",
                details={"field": "amount", "remaining": str(remaining), "paid_amount": str(total_paid + amount)}
            )

        try:
            redis_client.setex(cache_key, 3600, json.dumps(True))
        except redis.RedisError as e:
            logger.warning(f"Failed to cache payment amount: {str(e)}")

        logger.info(f"Validated payment amount {amount} for invoice {invoice.invoice_number}, remaining: {remaining}")
        return True
    except Exception as e:
        inv_num = getattr(invoice, 'invoice_number', str(invoice))
        logger.error(f"Failed to validate payment amount for invoice {inv_num}: {str(e)}", exc_info=True)
        raise InvoiceValidationError(
            message=f"Failed to validate payment amount: {str(e)}",
            code="payment_amount_validation_failed",
            details={"error": str(e)}
        )

@transaction.atomic
def validate_payment_reference(payment_reference, payment_method_code, invoice, payment_id=None):
    from invoices.models.invoice import Invoice
    from invoices.models.payment import Payment
    """Validate payment reference format and uniqueness."""
    logger.debug(f"Validating payment reference {payment_reference} for invoice {invoice.invoice_number}")
    try:
        if not isinstance(invoice, Invoice) or not Invoice.objects.filter(id=invoice.id, is_active=True).exists():
            raise InvoiceValidationError(
                message="Invoice does not exist or is inactive.",
                code="invalid_invoice",
                details={"field": "invoice", "invoice_id": invoice.id if hasattr(invoice, 'id') else None}
            )

        if payment_reference:
            if len(payment_reference) > PAYMENT_REFERENCE_MAX_LENGTH:
                raise InvoiceValidationError(
                    message=f"Payment reference cannot exceed {PAYMENT_REFERENCE_MAX_LENGTH} characters.",
                    code="invalid_payment_reference",
                    details={"field": "payment_reference", "value": payment_reference}
                )

            cache_key_ref = f"payment:reference:{payment_reference}:{payment_method_code}"
            try:
                cached_valid = redis_client.get(cache_key_ref)
                if cached_valid:
                    return json.loads(cached_valid)
            except redis.RedisError as e:
                logger.warning(f"Redis cache miss for payment reference {payment_reference}: {str(e)}")
                raise InvoiceValidationError(
                    message="Failed to access cache for payment reference validation.",
                    code="redis_connection_error",
                    details={"error": str(e)}
                )

            if payment_method_code == 'UPI':
                if not re.match(r'^[a-zA-Z0-9.\-@]{1,50}$', payment_reference):
                    raise InvoiceValidationError(
                        message="Invalid UPI reference format.",
                        code="invalid_upi_reference",
                        details={"field": "payment_reference", "value": payment_reference}
                    )

            cache_key_unique = f"payment:reference:invoice:{invoice.id}:{payment_reference}"
            try:
                cached_unique = redis_client.get(cache_key_unique)
                if cached_unique and (not payment_id or int(cached_unique) != payment_id):
                    raise InvoiceValidationError(
                        message="Payment reference already exists for this invoice.",
                        code="duplicate_payment_reference",
                        details={"field": "payment_reference", "value": payment_reference}
                    )
            except redis.RedisError as e:
                logger.warning(f"Redis cache miss for payment reference uniqueness: {str(e)}")
                raise InvoiceValidationError(
                    message="Failed to access cache for payment reference uniqueness.",
                    code="redis_connection_error",
                    details={"error": str(e)}
                )

            if Payment.objects.filter(
                invoice=invoice,
                payment_reference=payment_reference,
                is_active=True
            ).exclude(pk=payment_id).exists():
                try:
                    redis_client.setex(cache_key_unique, 3600, str(payment_id or 0))
                except redis.RedisError as e:
                    logger.warning(f"Failed to cache payment reference: {str(e)}")
                raise InvoiceValidationError(
                    message="Payment reference already exists for this invoice.",
                    code="duplicate_payment_reference",
                    details={"field": "payment_reference", "value": payment_reference}
                )

            try:
                redis_client.setex(cache_key_ref, 3600, json.dumps(True))
                redis_client.setex(cache_key_unique, 3600, str(payment_id or 0))
            except redis.RedisError as e:
                logger.warning(f"Failed to cache payment reference: {str(e)}")

        logger.info(f"Validated payment reference {payment_reference} for invoice {invoice.invoice_number}")
        return True
    except Exception as e:
        logger.error(f"Failed to validate payment reference for invoice {invoice.invoice_number}: {str(e)}", exc_info=True)
        raise InvoiceValidationError(
            message=f"Failed to validate payment reference: {str(e)}",
            code="payment_reference_validation_failed",
            details={"error": str(e)}
        )

def validate_payment_method(payment_method, exclude_pk=None):
    from invoices.models.payment_method import PaymentMethod
    """Validate PaymentMethod object."""
    logger.debug(f"Validating PaymentMethod: {payment_method.code or 'New Payment Method'}")
    try:
        if not isinstance(payment_method, PaymentMethod):
            raise InvoiceValidationError(
                message="Invalid payment method object.",
                code="invalid_payment_method",
                details={"payment_method_id": getattr(payment_method, 'id', None)}
            )

        # Validate code
        if not payment_method.code:
            raise InvoiceValidationError(
                message="Payment method code is required.",
                code="invalid_payment_method_code",
                details={"field": "code"}
            )
        if len(payment_method.code) > PAYMENT_METHOD_CODE_MAX_LENGTH:
            raise InvoiceValidationError(
                message=f"Payment method code cannot exceed {PAYMENT_METHOD_CODE_MAX_LENGTH} characters.",
                code="invalid_payment_method_code",
                details={"field": "code", "value": payment_method.code}
            )
        if not payment_method.code.isalnum():
            raise InvoiceValidationError(
                message="Payment method code must be alphanumeric.",
                code="invalid_payment_method_code",
                details={"field": "code", "value": payment_method.code}
            )
        if PaymentMethod.objects.filter(code=payment_method.code, is_active=True, deleted_at__isnull=True).exclude(pk=exclude_pk).exists():
            raise InvoiceValidationError(
                message="Payment method code already exists.",
                code="duplicate_payment_method_code",
                details={"field": "code", "value": payment_method.code}
            )

        # Validate name
        if not payment_method.name:
            raise InvoiceValidationError(
                message="Payment method name is required.",
                code="invalid_payment_method_name",
                details={"field": "name"}
            )
        if len(payment_method.name) > PAYMENT_METHOD_NAME_MAX_LENGTH:
            raise InvoiceValidationError(
                message=f"Payment method name cannot exceed {PAYMENT_METHOD_NAME_MAX_LENGTH} characters.",
                code="invalid_payment_method_name",
                details={"field": "name", "value": payment_method.name}
            )

        # Validate description
        if payment_method.description and len(payment_method.description) > DESCRIPTION_MAX_LENGTH:
            raise InvoiceValidationError(
                message=f"Description cannot exceed {DESCRIPTION_MAX_LENGTH} characters.",
                code="invalid_description",
                details={"field": "description", "value": payment_method.description}
            )

        logger.info(f"Validated PaymentMethod: {payment_method.code}")
        return True
    except Exception as e:
        logger.error(f"Failed to validate PaymentMethod: {str(e)}", exc_info=True)
        raise InvoiceValidationError(
            message=f"Failed to validate payment method: {str(e)}",
            code="invalid_fields",
            details={"error": str(e)}
        )

@transaction.atomic
def validate_payment_status(payment, exclude_pk=None):
    from invoices.models.payment import Payment
    """Validate payment status."""
    logger.debug(f"Validating payment status for invoice {payment.invoice.invoice_number}")
    try:
        if not isinstance(payment, Payment):
            raise InvoiceValidationError(
                message="Invalid payment object.",
                code="invalid_payment",
                details={"payment_id": getattr(payment, 'id', None)}
            )

        if payment.status not in ['PENDING', 'COMPLETED', 'FAILED']:
            raise InvoiceValidationError(
                message=f"Payment status must be one of PENDING, COMPLETED, FAILED, got {payment.status}.",
                code="invalid_payment_status",
                details={"field": "status", "value": payment.status}
            )

        cache_key = f"payment:status:{payment.id or 'new'}:{payment.status}"
        try:
            cached_valid = redis_client.get(cache_key)
            if cached_valid:
                return json.loads(cached_valid)
        except redis.RedisError as e:
            logger.warning(f"Redis cache miss for payment status {payment.status}: {str(e)}")
            raise InvoiceValidationError(
                message="Failed to access cache for payment status validation.",
                code="redis_connection_error",
                details={"error": str(e)}
            )

        validate_payment_amount(payment.amount, payment.invoice, payment_id=exclude_pk)
        validate_payment_reference(payment.payment_reference, payment.payment_method.code, payment.invoice, payment_id=exclude_pk)
        validate_payment_method(payment.payment_method.code, payment.invoice)

        try:
            redis_client.setex(cache_key, 3600, json.dumps(True))
        except redis.RedisError as e:
            logger.warning(f"Failed to cache payment status: {str(e)}")

        logger.info(f"Validated payment for invoice {payment.invoice.invoice_number}")
        return True
    except Exception as e:
        logger.error(f"Failed to validate payment for invoice {payment.invoice.invoice_number}: {str(e)}", exc_info=True)
        raise InvoiceValidationError(
            message=f"Failed to validate payment: {str(e)}",
            code="payment_status_validation_failed",
            details={"error": str(e)}
        )
