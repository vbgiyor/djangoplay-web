import logging

import phonenumbers
from django.core.exceptions import ValidationError

logger = logging.getLogger('utilities.utils')

def validate_phone_number(value, country_code=None):
    """
    Validate a phone number, optionally with a specified country code.

    Args:
        value (str): The phone number to validate.
        country_code (str, optional): The country code (e.g., 'US', 'IN'). If provided,
                                     validates the phone number against the country's dial code from the database.

    Raises:
        ValidationError: If the phone number or country code is invalid.

    """
    from locations.models.custom_country import CustomCountry
    # Check if the provided country code is valid
    expected_dial_code = None
    if country_code:
        try:
            country = CustomCountry.objects.get(country_code=country_code.upper())
            if country.country_phone_code:
                # Normalize phone code: add '+' if missing, remove '-' and extra spaces
                expected_dial_code = f"+{country.country_phone_code.lstrip('+').replace('-', '').strip()}"
            else:
                # Handle missing phone code with a fallback for known countries
                expected_dial_code = '+91' if country_code.upper() == 'IN' else None
            if not expected_dial_code:
                # Allow validation without dial code check if none is available
                logger.debug(f"No phone code defined for country: {country_code}. Skipping dial code validation.")
        except CustomCountry.DoesNotExist:
            raise ValidationError(f"Invalid country code: {country_code}")

    try:
        # Parse the phone number
        phone_number = phonenumbers.parse(value, country_code if country_code else None)

        # If expected dial code is provided, validate it
        if country_code and expected_dial_code:
            actual_dial_code = f"+{phone_number.country_code}"
            # Handle multiple dial codes (e.g., split by '/')
            expected_dial_codes = expected_dial_code.split('/') if '/' in expected_dial_code else [expected_dial_code]
            if actual_dial_code not in expected_dial_codes:
                raise ValidationError(f"Phone number does not match the country code {expected_dial_code} for {country_code}.")

        # For India, ensure the number is a valid mobile number (10 digits, starting with 6-9)
        if country_code and country_code.upper() == 'IN':
            national_number = str(phone_number.national_number)
            if not (len(national_number) == 10 and national_number[0] in '6789'):
                raise ValidationError("Indian phone numbers must be 10 digits and start with 6, 7, 8, or 9.")

        # Validate the phone number
        if not phonenumbers.is_valid_number(phone_number):
            raise ValidationError("Invalid phone number.")
    except phonenumbers.phonenumberutil.NumberParseException as e:
        raise ValidationError(f"Invalid phone number format: {str(e)}")
