import re

from django.core.exceptions import ValidationError
from django_countries import countries


def validate_postal_code(postal_code, country_code):
    """Validate postal code based on country-specific formats."""
    postal_code = postal_code.strip()
    patterns = {
        'US': r'^\d{5}(-\d{4})?$',  # e.g., 12345 or 12345-6789
        'CA': r'^[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d$',  # e.g., A1B 2C3
        'IN': r'^\d{6}$',  # e.g., 123456
        'GB': r'^[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}$',  # e.g., SW1A 1AA
        'AU': r'^\d{4}$',  # e.g., 2000
        # Add more country patterns as needed
    }

    pattern = patterns.get(country_code)
    if pattern and not re.match(pattern, postal_code):
        raise ValidationError(
            f"Invalid postal code format for {countries.name(country_code)}. "
            f"Expected format: {pattern}"
        )

    if not pattern and postal_code:
        # For countries without specific patterns, ensure length is reasonable
        if len(postal_code) > 20:
            raise ValidationError("Postal code is too long.")

def validate_state_country_match(state, country):
    """Ensure the state belongs to the specified country."""
    if state and country and state.country != country:
        raise ValidationError(
            f"State {state.name} does not belong to country {country.name}."
        )
