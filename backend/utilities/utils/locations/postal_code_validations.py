import logging
import re

from django.core.exceptions import ValidationError
from locations.models.custom_country import CustomCountry

logger = logging.getLogger(__name__)

class PostalCodeValidationError(ValidationError):

    """Custom exception for postal code validation errors."""

    pass

def get_country_postal_regex(country_code: str) -> str | None:
    """
    Retrieve the postal code regex for a country from the CustomCountry model.

    Args:
        country_code (str): The ISO country code (e.g., 'IN', 'US').

    Returns:
        Optional[str]: The regex pattern for the postal code, or None if not found.

    Raises:
        PostalCodeValidationError: If the country does not exist.

    """
    try:
        country = CustomCountry.objects.get(country_code=country_code.upper())
        if not country.has_postal_code:
            logger.debug(f"Country {country_code} does not use postal codes.")
            return None
        if country.postal_code_regex:
            logger.debug(f"Found postal code regex for {country_code}: {country.postal_code_regex}")
            return country.postal_code_regex
        logger.warning(f"No postal code regex found for country: {country_code}")
        return None
    except CustomCountry.DoesNotExist:
        logger.warning(f"Country '{country_code}' not found in CustomCountry.")
        raise PostalCodeValidationError(f"Country '{country_code}' not found.")

def validate_postal_code_with_regex(postal_code: str, regex: str) -> str:
    """
    Validate a postal code against a provided regex pattern.

    Args:
        postal_code (str): The postal code to validate.
        regex (str): The regex pattern to match against.

    Returns:
        str: The validated postal code.

    Raises:
        PostalCodeValidationError: If the postal code or regex is invalid.

    """
    try:
        compiled_pattern = re.compile(regex)
        if not compiled_pattern.match(postal_code):
            logger.error(f"Postal code '{postal_code}' does not match regex '{regex}'")
            raise PostalCodeValidationError(f"Invalid postal code format: '{postal_code}'")
        logger.debug(f"Postal code '{postal_code}' validated successfully with regex '{regex}'")
        return postal_code
    except re.error as e:
        logger.error(f"Invalid regex pattern '{regex}': {e}")
        raise PostalCodeValidationError(f"Invalid regex pattern for postal code validation: {e}")

def validate_postal_code(postal_code: str | None, country_code: str, regex: str | None = None) -> str | None:
    """
    Validate a postal code based on country-specific regex from CustomCountry model or provided regex.

    Args:
        postal_code (Optional[str]): The postal code to validate. Can be None or empty for countries without postal codes.
        country_code (str): The ISO country code (e.g., 'US', 'CA').
        regex (Optional[str]): A custom regex pattern to use for validation, overriding database patterns.

    Returns:
        Optional[str]: The validated postal code, or None if no postal code is required.

    Raises:
        PostalCodeValidationError: If the postal code is invalid, the country does not use postal codes, or other errors occur.

    """
    if not country_code:
        logger.error("Country code cannot be empty.")
        raise PostalCodeValidationError("Country code is required.")

    country_code = country_code.upper().strip()
    postal_code = postal_code.strip() if postal_code else None
    logger.debug(f"Validating postal code: '{postal_code}' for country: '{country_code}'")

    try:
        country = CustomCountry.objects.get(country_code=country_code)
        if not country.has_postal_code:
            if postal_code:
                logger.error(f"Postal code provided for country without postal codes: {country_code}")
                raise PostalCodeValidationError(f"Country '{country_code}' does not use postal codes.")
            logger.debug(f"No postal code required for {country_code}.")
            return None

        if not postal_code:
            logger.error(f"Postal code is required for country: {country_code}")
            raise PostalCodeValidationError(f"Postal code is required for country '{country_code}'.")

        if regex:
            logger.debug(f"Using provided regex for validation: {regex}")
            return validate_postal_code_with_regex(postal_code, regex)

        regex = get_country_postal_regex(country_code)
        if regex:
            return validate_postal_code_with_regex(postal_code, regex)

        logger.warning(f"No postal code regex defined for country: {country_code}, accepting postal code as is.")
        return postal_code

    except CustomCountry.DoesNotExist:
        logger.warning(f"No validation performed for unknown country: {country_code}")
        raise PostalCodeValidationError(f"Country '{country_code}' not found.")
