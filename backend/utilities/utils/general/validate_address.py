import logging
import re

from django.core.exceptions import ValidationError
from locations.models.custom_country import CustomCountry

logger = logging.getLogger('locations.validate_address')

def validate_address(postal_code: str, country_code: str) -> None:
    """Validate a postal code against the country's regex."""
    country = CustomCountry.objects.filter(country_code=country_code).first()
    if not country:
        raise ValidationError(f"Country code {country_code} not found")
    if country.has_postal_code and not postal_code:
        raise ValidationError(f"Postal code is required for {country.name}")
    if postal_code and country.postal_code_regex:
        try:
            regex = re.compile(country.postal_code_regex)
            if not regex.match(postal_code):
                raise ValidationError(f"Invalid postal code '{postal_code}' for {country.name}")
            logger.debug(f"Validated postal code '{postal_code}' for {country.name}")
        except re.error as e:
            logger.error(f"Invalid regex for {country.name}: {country.postal_code_regex}, error: {e}")
            raise ValidationError(f"Cannot validate postal code due to invalid regex for {country.name}")
