# import logging
# import redis
# from django.db import transaction
# from invoices.exceptions import InvoiceValidationError
# from utilities.utils.general.normalize_text import normalize_text
# from core.utils.redis_client import redis_client

# logger = logging.getLogger(__name__)

# @transaction.atomic
# def validate_status(status, exclude_pk=None):
#     """
#     Validate the Status object.

#     Note: The `name` and `code` fields are treated case-insensitively during validation
#     (using `iexact` queries and lowercase cache keys) to ensure consistency, despite
#     case-sensitive database constraints.
#     """
#     from invoices.models.status import Status
#     logger.debug(f"Validating Status: {status.name or 'Unnamed'}")
#     try:
#         if not isinstance(status, Status):
#             raise InvoiceValidationError(
#                 message="Invalid status object.",
#                 code="invalid_status",
#                 details={"status_id": getattr(status, 'id', None)}
#             )

#         # Validate name
#         if not status.name or not status.name.strip():
#             raise InvoiceValidationError(
#                 message="Status name cannot be empty or whitespace.",
#                 code="empty_name",
#                 details={"field": "name"}
#             )

#         # Normalize name and code
#         status.name = normalize_text(status.name)
#         status.code = normalize_text(status.code)

#         # Check for duplicate name
#         cache_key_name = f"status:name:{status.name.lower()}"
#         try:
#             cached_name = redis_client.get(cache_key_name)
#             if cached_name and (not exclude_pk or int(cached_name) != exclude_pk):
#                 if status.code == 'DRAFT':
#                     logger.warning(f"Allowing DRAFT status creation despite existing name {status.name}")
#                 else:
#                     raise InvoiceValidationError(
#                         message="A status with this name already exists.",
#                         code="duplicate_status_name",
#                         details={"field": "name", "value": status.name}
#                     )
#         except redis.RedisError as e:
#             logger.warning(f"Redis cache miss for status name {status.name}: {str(e)}")
#             # Continue without cache check

#         existing_status = Status.objects.filter(name__iexact=status.name)
#         if exclude_pk:
#             existing_status = existing_status.exclude(pk=exclude_pk)
#         if existing_status.exists():
#             if status.code == 'DRAFT':
#                 logger.warning(f"Allowing DRAFT status creation despite existing name {status.name}")
#             else:
#                 raise InvoiceValidationError(
#                     message="A status with this name already exists.",
#                     code="duplicate_status_name",
#                     details={"field": "name", "value": status.name}
#                 )

#         # Validate code
#         if not status.code or not status.code.strip():
#             raise InvoiceValidationError(
#                 message="Status code cannot be empty or whitespace.",
#                 code="empty_code",
#                 details={"field": "code"}
#             )

#         cache_key_code = f"status:code:{status.code.lower()}"
#         try:
#             cached_code = redis_client.get(cache_key_code)
#             if cached_code and (not exclude_pk or int(cached_code) != exclude_pk):
#                 if status.code == 'DRAFT':
#                     logger.warning(f"Allowing DRAFT status creation despite existing code {status.code}")
#                 else:
#                     raise InvoiceValidationError(
#                         message="A status with this code already exists.",
#                         code="duplicate_status_code",
#                         details={"field": "code", "value": status.code}
#                     )
#         except redis.RedisError as e:
#             logger.warning(f"Redis cache miss for status code {status.code}: {str(e)}")
#             # Continue without cache check

#         existing_code = Status.objects.filter(code__iexact=status.code)
#         if exclude_pk:
#             existing_code = existing_code.exclude(pk=exclude_pk)
#         if existing_code.exists():
#             # Allow DRAFT if existing status is inactive or soft-deleted
#             existing = existing_code.first()
#             if status.code == 'DRAFT' and (not existing.is_active or existing.deleted_at):
#                 logger.warning(f"Allowing DRAFT status creation; existing code {status.code} is inactive or deleted")
#             else:
#                 raise InvoiceValidationError(
#                     message="A status with this code already exists.",
#                     code="duplicate_status_code",
#                     details={"field": "code", "value": status.code}
#                 )

#         # Validate default status
#         if status.is_default and Status.objects.filter(is_default=True).exclude(pk=exclude_pk).exists():
#             raise InvoiceValidationError(
#                 message="Another status is already set as default.",
#                 code="multiple_defaults",
#                 details={"field": "is_default"}
#             )

#         logger.info(f"Validated Status: {status.name}")
#         return True
#     except Exception as e:
#         logger.error(f"Failed to validate Status {status.name or 'Unnamed'}: {str(e)}", exc_info=True)
#         raise InvoiceValidationError(
#             message=f"Failed to validate status: {str(e)}",
#             code="status_validation_failed",
#             details={"error": str(e)}
#         )

# @transaction.atomic
# def cache_status(status):
#     """Cache the status name and code in Redis after a successful save."""
#     try:
#         cache_key_name = f"status:name:{status.name.lower()}"
#         cache_key_code = f"status:code:{status.code.lower()}"
#         redis_client.setex(cache_key_name, 3600, str(status.id))
#         redis_client.setex(cache_key_code, 3600, str(status.id))
#         logger.debug(f"Cached status: {status.name} (ID: {status.id})")
#     except redis.RedisError as e:
#         logger.warning(f"Failed to cache status {status.name}: {str(e)}")


import logging

import redis
from core.utils.redis_client import redis_client
from django.db import transaction
from utilities.utils.general.normalize_text import normalize_text

from invoices.exceptions import InvoiceValidationError

logger = logging.getLogger(__name__)

@transaction.atomic
def validate_status(status, exclude_pk=None):
    """
    Validate the Status object.

    Note: The `name` and `code` fields are treated case-insensitively during validation
    (using `iexact` queries and lowercase cache keys) to ensure consistency, despite
    case-sensitive database constraints.
    """
    from invoices.models.status import Status
    logger.debug(f"Validating Status: {status.name or 'Unnamed'}")
    try:
        if not isinstance(status, Status):
            raise InvoiceValidationError(
                message="Invalid status object.",
                code="invalid_status",
                details={"status_id": getattr(status, 'id', None)}
            )

        # Validate name
        if not status.name or not status.name.strip():
            raise InvoiceValidationError(
                message="Status name cannot be empty or whitespace.",
                code="empty_name",
                details={"field": "name"}
            )

        # Normalize name and code
        status.name = normalize_text(status.name)
        status.code = normalize_text(status.code)

        # Check for duplicate name
        cache_key_name = f"status:name:{status.name.lower()}"
        try:
            cached_name = redis_client.get(cache_key_name)
            if cached_name and (not exclude_pk or int(cached_name) != exclude_pk):
                if status.code == 'DRAFT':
                    logger.warning(f"Allowing DRAFT status creation despite existing name {status.name}")
                else:
                    raise InvoiceValidationError(
                        message="A status with this name already exists.",
                        code="duplicate_status_name",
                        details={"field": "name", "value": status.name}
                    )
        except redis.RedisError as e:
            logger.warning(f"Redis cache miss for status name {status.name}: {str(e)}")
            # Continue without cache check

        existing_status = Status.objects.filter(name__iexact=status.name)
        if exclude_pk:
            existing_status = existing_status.exclude(pk=exclude_pk)
        if existing_status.exists():
            if status.code == 'DRAFT':
                logger.warning(f"Allowing DRAFT status creation despite existing name {status.name}")
            else:
                raise InvoiceValidationError(
                    message="A status with this name already exists.",
                    code="duplicate_status_name",
                    details={"field": "name", "value": status.name}
                )

        # Validate code
        if not status.code or not status.code.strip():
            raise InvoiceValidationError(
                message="Status code cannot be empty or whitespace.",
                code="empty_code",
                details={"field": "code"}
            )

        cache_key_code = f"status:code:{status.code.lower()}"
        try:
            cached_code = redis_client.get(cache_key_code)
            if cached_code and (not exclude_pk or int(cached_code) != exclude_pk):
                raise InvoiceValidationError(
                    message="A status with this code already exists.",
                    code="duplicate_status_code",
                    details={"field": "code", "value": status.code}
                )
        except redis.RedisError as e:
            logger.warning(f"Redis cache miss for status code {status.code}: {str(e)}")
            # Continue without cache check

        existing_code = Status.objects.filter(code__iexact=status.code)
        if exclude_pk:
            existing_code = existing_code.exclude(pk=exclude_pk)
        if existing_code.exists():
            raise InvoiceValidationError(
                message="A status with this code already exists.",
                code="duplicate_status_code",
                details={"field": "code", "value": status.code}
            )

        # Validate default status
        if status.is_default and Status.objects.filter(is_default=True).exclude(pk=exclude_pk).exists():
            raise InvoiceValidationError(
                message="Another status is already set as default.",
                code="multiple_defaults",
                details={"field": "is_default"}
            )

        logger.info(f"Validated Status: {status.name}")
        return True
    except Exception as e:
        logger.error(f"Failed to validate Status {status.name or 'Unnamed'}: {str(e)}", exc_info=True)
        raise InvoiceValidationError(
            message=f"Failed to validate status: {str(e)}",
            code="status_validation_failed",
            details={"error": str(e)}
        )

@transaction.atomic
def cache_status(status):
    """Cache the status name and code in Redis after a successful save."""
    try:
        cache_key_name = f"status:name:{status.name.lower()}"
        cache_key_code = f"status:code:{status.code.lower()}"
        redis_client.setex(cache_key_name, 3600, str(status.id))
        redis_client.setex(cache_key_code, 3600, str(status.id))
        logger.debug(f"Cached status: {status.name} (ID: {status.id})")
    except redis.RedisError as e:
        logger.warning(f"Failed to cache status {status.name}: {str(e)}")
