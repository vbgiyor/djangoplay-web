import logging
import re

from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


def is_valid_indian_pan(pan_number):
    """Validate an Indian PAN number."""
    if not pan_number:
        return False
    pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
    return bool(re.match(pattern, pan_number.strip()))


def validate_gstin(value):
    """
    Goods and Services Tax Identification Number. Validate Indian GSTIN format (15 characters, specific pattern).
    Breakdown of the 15 digits:
       - First two digits – State code (based on the state in which the taxpayer is registered)
       - Next 10 digits – PAN (Permanent Account Number) of the business or individual
       - 13th digit – Entity code (if the taxpayer has multiple registrations in the same state)
       - 14th digit – Default "Z" (used for future use, no practical significance as of now)
       - 15th digit – Check code (used for validation)
       - Example: 27AAAAA1234A1Z5
    """
    logger.debug(f"Validating GSTIN: {value}")
    if value and not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', value):
        logger.error(f"Invalid GSTIN: {value}")
        raise ValidationError('Invalid GSTIN format.')
    return value
