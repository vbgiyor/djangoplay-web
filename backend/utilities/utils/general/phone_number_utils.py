import logging
import random

import phonenumbers
from django.core.exceptions import ValidationError
from locations.models.custom_country import CustomCountry
from phonenumbers import NumberParseException, PhoneNumberFormat, PhoneNumberType

logger = logging.getLogger(__name__)

def generate_phone_number(country_code: str) -> str:
    """
    Generate a valid phone number for the specified country code using phonenumbers library.

    Args:
        country_code (str): ISO country code (e.g., 'IN', 'US', 'FR', 'KR').

    Returns:
        str: A valid phone number in international format (e.g., '+33612345678').

    Raises:
        ValidationError: If a valid phone number cannot be generated or country data is missing.

    """
    try:
        country_code = country_code.upper()
        # Step 1: Fetch country phone code and phone number length from CustomCountry
        country = CustomCountry.objects.get(country_code=country_code)
        country_phone_code = f"+{country.country_phone_code.lstrip('+').strip()}"

        # Get phone number length from the database
        if not country.phone_number_length:
            logger.warning(f"No phone number length specified for {country_code}, falling back to metadata")
            metadata = phonenumbers.PhoneMetadata.metadata_for_region(country_code)
            possible_lengths = metadata.mobile.possible_length if metadata and metadata.mobile else [10]
            national_number_length = random.choice(possible_lengths)
        else:
            try:
                national_number_length = int(country.phone_number_length)
            except ValueError:
                logger.error(f"Invalid phone_number_length for {country_code}: {country.phone_number_length}")
                raise ValidationError(f"Invalid phone number length for {country_code}")

        # Step 2: Get phone number metadata for the country
        metadata = phonenumbers.PhoneMetadata.metadata_for_region(country_code)
        if not metadata or not metadata.mobile:
            logger.error(f"No mobile number metadata available for {country_code}")
            raise ValidationError(f"No mobile number metadata available for {country_code}")

        # Extract possible mobile prefixes
        mobile_prefixes = []
        if hasattr(metadata.mobile, 'national_prefix_for_parsing') and metadata.mobile.national_prefix_for_parsing:
            mobile_prefixes = metadata.mobile.national_prefix_for_parsing.split('|')
        elif metadata.mobile.example_number:
            example_number = phonenumbers.parse(metadata.mobile.example_number, country_code)
            prefix = str(example_number.national_number)[:2]
            mobile_prefixes = [prefix]
        else:
            logger.warning(f"No specific mobile prefixes found for {country_code}, using generic digits")
            mobile_prefixes = ['1', '2', '3', '4', '5', '6', '7', '8', '9']

        # Step 3: Generate phone number
        max_attempts = 50
        for attempt in range(max_attempts):
            try:
                # Select a random prefix
                prefix = random.choice(mobile_prefixes)
                remaining_length = national_number_length - len(prefix)
                if remaining_length < 0:
                    logger.debug(f"Invalid prefix length for {country_code}: prefix={prefix}, required_length={national_number_length}")
                    continue

                # Generate random digits for the remaining length
                national_number = prefix + ''.join(random.choices('0123456789', k=remaining_length))
                phone_number = f"{country_phone_code}{national_number}"

                # Step 4: Validate phone number
                parsed_number = phonenumbers.parse(phone_number, country_code)
                if (phonenumbers.is_valid_number(parsed_number) and
                        phonenumbers.number_type(parsed_number) in [PhoneNumberType.MOBILE,
                                                                   PhoneNumberType.FIXED_LINE_OR_MOBILE]):
                    formatted_number = phonenumbers.format_number(parsed_number, PhoneNumberFormat.INTERNATIONAL)
                    logger.debug(f"Generated valid phone number {formatted_number} for {country_code} on attempt {attempt + 1}")
                    return formatted_number
                else:
                    logger.debug(f"Phone number {phone_number} invalid for {country_code} on attempt {attempt + 1}: "
                                 f"is_valid={phonenumbers.is_valid_number(parsed_number)}, "
                                 f"number_type={phonenumbers.number_type(parsed_number)}")
            except NumberParseException as e:
                logger.debug(f"Phone number {phone_number} invalid for {country_code} on attempt {attempt + 1}: {str(e)}")

        # Fallback to example number if available
        try:
            example_number = phonenumbers.example_number_for_type(country_code, PhoneNumberType.MOBILE)
            formatted_number = phonenumbers.format_number(example_number, PhoneNumberFormat.INTERNATIONAL)
            logger.warning(f"Using example phone number {formatted_number} for {country_code} as fallback")
            return formatted_number
        except NumberParseException:
            logger.error(f"Failed to generate valid phone number for {country_code} after {max_attempts} attempts")
            raise ValidationError(f"Failed to generate valid phone number for {country_code}")

    except CustomCountry.DoesNotExist:
        logger.error(f"Country {country_code} not found in CustomCountry")
        raise ValidationError(f"Country {country_code} not found in CustomCountry")
    except Exception as e:
        logger.error(f"Error generating phone number for {country_code}: {str(e)}")
        raise ValidationError(f"Error generating phone number for {country_code}: {str(e)}")
