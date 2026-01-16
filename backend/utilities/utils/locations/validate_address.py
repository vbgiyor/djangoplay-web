import logging
import re

from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

def validate_address(postal_code: str, country_code: str, country_name: str, has_postal_code: bool, postal_code_regex: str = None) -> None:
    """
    Validate a postal code against a country's postal code regex.

    Args:
        postal_code (str): The postal code to validate.
        country_code (str): ISO country code.
        country_name (str): Country name for error messages.
        has_postal_code (bool): Whether this country requires a postal code.
        postal_code_regex (str, optional): Regex to validate the postal code format.

    """
    if has_postal_code and not postal_code:
        raise ValidationError(f"Postal code is required for {country_name} ({country_code})")

    if postal_code and postal_code_regex:
        try:
            regex = re.compile(postal_code_regex)
            if not regex.match(postal_code):
                raise ValidationError(f"Invalid postal code '{postal_code}' for {country_name} ({country_code})")
            logger.debug(f"Validated postal code '{postal_code}' for {country_name} ({country_code})")
        except re.error as e:
            logger.error(f"Invalid regex for {country_name} ({country_code}): {postal_code_regex}, error: {e}")
            raise ValidationError(f"Cannot validate postal code due to invalid regex for {country_name} ({country_code})")
