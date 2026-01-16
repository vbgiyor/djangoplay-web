import logging
import random
import re
from string import ascii_uppercase, digits

from django.core.exceptions import ValidationError
from locations.models.custom_country import CustomCountry
from utilities.utils.locations.postal_code_validations import PostalCodeValidationError, validate_postal_code

logger = logging.getLogger('utilities.utils')

def generate_postal_code(country_code: str) -> str:
    """
    Generate a valid postal code for the specified country code using the postal_code_regex from CustomCountry.

    Args:
        country_code (str): ISO country code (e.g., 'IN', 'US', 'NZ').

    Returns:
        str: A valid postal code matching the country's regex (e.g., '123456' for IN, '12345' for US).

    Raises:
        ValidationError: If a valid postal code cannot be generated, regex is invalid/missing, or postal codes are not supported.

    """
    try:
        country_code = country_code.upper()
        # Fetch postal code regex from CustomCountry
        try:
            country = CustomCountry.objects.get(country_code=country_code)
            if not country.has_postal_code:
                logger.info(f"Country {country_code} does not support postal codes")
                raise ValidationError(f"Postal codes are not supported for {country_code}")
            postal_code_regex = country.postal_code_regex
            if not postal_code_regex:
                logger.warning(f"Postal code regex missing for {country_code}")
                raise ValidationError(f"No postal code regex defined for {country_code}")
        except CustomCountry.DoesNotExist:
            logger.warning(f"Country {country_code} not found in CustomCountry")
            raise ValidationError(f"Country {country_code} not found")

        # Validate regex
        try:
            re.compile(postal_code_regex)
        except re.error as e:
            logger.error(f"Invalid postal code regex for {country_code}: {str(e)}")
            raise ValidationError(f"Invalid postal code regex for {country_code}: {str(e)}")

        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                # Generate postal code based on regex pattern
                postal_code = _generate_postal_code_from_regex(postal_code_regex, country_code)

                # Validate generated postal code using validate_postal_code
                validated_postal_code = validate_postal_code(postal_code, country_code)
                logger.debug(f"Generated and validated postal code {validated_postal_code} for {country_code} on attempt {attempt + 1}")
                return validated_postal_code
            except (PostalCodeValidationError, ValidationError) as e:
                logger.debug(f"Generated postal code {postal_code} invalid for {country_code} on attempt {attempt + 1}: {str(e)}")

            if attempt == max_attempts - 1:
                logger.error(f"Failed to generate valid postal code for {country_code} after {max_attempts} attempts")
                raise ValidationError(f"Failed to generate valid postal code for {country_code}")

    except Exception as e:
        logger.error(f"Error generating postal code for {country_code}: {str(e)}")
        raise ValidationError(f"Error generating postal code for {country_code}: {str(e)}")

def _generate_postal_code_from_regex(regex: str, country_code: str) -> str:
    """
    Generate a postal code based on the provided regex pattern.

    Args:
        regex (str): Postal code regex pattern.
        country_code (str): ISO country code for logging context.

    Returns:
        str: Generated postal code.

    """
    # Simplify regex handling for common patterns
    if country_code == 'IN':
        # India: 6 digits
        return ''.join(random.choices(digits, k=6))
    elif country_code == 'US':
        # US: 5 digits
        return ''.join(random.choices(digits, k=5))
    elif country_code == 'CA':
        # Canada: A1A 1A1
        return (random.choice(ascii_uppercase) +
                random.choice(digits) +
                random.choice(ascii_uppercase) + ' ' +
                random.choice(digits) +
                random.choice(ascii_uppercase) +
                random.choice(digits))
    else:
        # Generic generation based on regex length and character types
        try:
            # Estimate length and character types from regex
            sample = ''
            if 'd' in regex or '[0-9]' in regex:
                sample += ''.join(random.choices(digits, k=regex.count('d') or regex.count('[0-9]')))
            if 'w' in regex or '[A-Za-z]' in regex:
                sample += ''.join(random.choices(ascii_uppercase, k=regex.count('w') or regex.count('[A-Za-z]')))
            if len(sample) == 0:
                # Default to alphanumeric if regex is too complex
                sample = ''.join(random.choices(digits + ascii_uppercase, k=5))
            return sample
        except Exception as e:
            logger.debug(f"Error generating postal code from regex for {country_code}: {str(e)}")
            raise
