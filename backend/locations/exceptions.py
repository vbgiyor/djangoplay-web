import logging

from django.core.exceptions import ValidationError

logger = logging.getLogger('locations.exceptions')

class InvalidLocationData(ValidationError):

    """
    Raised when location data (e.g., country, region, subregion, city, timezone, location) is invalid.

    This exception extends Django's ValidationError to provide structured error handling
    for validation failures across location-related models (GlobalRegion, CustomCountry,
    CustomRegion, CustomSubRegion, CustomCity, Location, Timezone). It supports single error messages,
    lists of errors, or field-specific error dictionaries, and includes custom error codes for
    programmatic handling.

    Attributes:
        message (str or dict or list): The error message(s) describing the validation failure.
        code (str): A specific code for the error type (e.g., 'invalid_country_code', 'invalid_region_name').
        details (dict): Additional context about the error, such as invalid fields, values, or operation details.

    Example:
        # Single error for CustomCountry
        raise InvalidLocationData("Country name is required.", code="missing_country_name")

        # Multiple field errors for CustomCity
        raise InvalidLocationData(
            {
                "name": "City name is required",
                "timezone": "Invalid timezone ID"
            },
            code="invalid_fields",
            details={"fields": ["name", "timezone"], "model": "CustomCity"}
        )

        # Multiple errors for CustomSubRegion
        raise InvalidLocationData(
            ["Subregion name is required", "Invalid region ID"],
            code="multiple_errors",
            details={"model": "CustomSubRegion"}
        )

    """

    def __init__(self, message, code=None, details=None):
        """
        Initialize the exception with a message, optional code, and details.

        Args:
            message (str or dict or list): Error message(s) or error dictionary/list.
            code (str, optional): Specific error code for programmatic handling.

        Examples:
                - GlobalRegion: 'missing_global_region_name', 'invalid_global_region_name', 'duplicate_global_region_name'
                - CustomCountry: 'missing_country_name', 'invalid_country_name', 'duplicate_country_name',
                                'invalid_country_code', 'invalid_currency_code', 'invalid_postal_code_regex',
                                'invalid_country_languages', 'invalid_phone_code'
                - CustomRegion: 'missing_region_name', 'invalid_region_name', 'duplicate_region_name',
                               'invalid_region_code', 'invalid_region_country'
                - CustomSubRegion: 'missing_subregion_name', 'invalid_subregion_name', 'duplicate_subregion_name',
                                  'invalid_subregion_code', 'invalid_subregion_region'
                - CustomCity: 'missing_city_name', 'invalid_city_name', 'duplicate_city_name',
                             'invalid_city_timezone', 'invalid_city_subregion', 'invalid_city_coordinates'
                - Location: 'missing_location_city', 'invalid_location_hierarchy', 'invalid_location_postal_code',
                           'invalid_location_coordinates', 'duplicate_location'
                - Timezone: 'missing_timezone_id', 'invalid_timezone_id', 'invalid_timezone_offset',
                            Co'duplicate_timezone_id', 'invalid_timezone_country_code'
                - Generic: 'invalid_fields', 'multiple_errors', 'invalid_location_data'
            details (dict, optional): Additional context for the error (e.g., invalid fields, values, model).

        """
        self.details = details or {}
        # Define valid error codes for location-related validations
        valid_codes = [
            'invalid_location_data', 'invalid_fields', 'multiple_errors', 'retrieve_error',
            # GlobalRegion
            'missing_global_region_name', 'invalid_global_region_name', 'duplicate_global_region_name',
            # CustomCountry
            'missing_country_name', 'invalid_country_name', 'duplicate_country_name',
            'invalid_country_code', 'invalid_currency_code', 'invalid_postal_code_regex',
            'invalid_country_languages', 'invalid_phone_code',
            # CustomRegion
            'missing_region_name', 'invalid_region_name', 'duplicate_region_name',
            'invalid_region_code', 'invalid_region_country',
            # CustomSubRegion
            'missing_subregion_name', 'invalid_subregion_name', 'duplicate_subregion_name',
            'invalid_subregion_code', 'invalid_subregion_region',
            # CustomCity
            'missing_city_name', 'invalid_city_name', 'duplicate_city_name',
            'invalid_city_timezone', 'invalid_city_subregion', 'invalid_city_coordinates',
            # Location
            'missing_location_city', 'invalid_location_hierarchy', 'invalid_location_postal_code',
            'invalid_location_coordinates', 'duplicate_location',
            # Timezone
            'missing_timezone_id', 'invalid_timezone_id', 'invalid_timezone_offset',
            'duplicate_timezone_id', 'invalid_timezone_country_code',
        ]
        if code and code not in valid_codes:
            logger.error(f"Invalid error code: {code}. Must be one of {valid_codes}")
            raise ValueError(f"Invalid error code: {code}. Must be one of {valid_codes}.")
        super().__init__(message, code=code or "invalid_location_data")

    def to_dict(self):
        """
        Convert the exception to a dictionary for API responses.

        Returns:
            dict: A dictionary containing the error message(s), code, and details.

        Example:
            {
                "error": "Multiple field errors",
                "code": "invalid_fields",
                "details": {
                    "fields": ["name", "timezone"],
                    "model": "CustomCity",
                    "errors": {"name": "City name is required", "timezone": "Invalid timezone ID"}
                }
            }

        """
        if isinstance(self.message, dict):
            error_message = "Multiple field errors"
            details = {"errors": self.message, **self.details}
        elif isinstance(self.message, list):
            error_message = "Multiple validation errors"
            details = {"errors": self.message, **self.details}
        else:
            error_message = str(self.message)
            details = self.details

        return {
            "error": error_message,
            "code": self.code,
            "details": details,
        }

    def __str__(self):
        """Return a string representation of the error."""
        if isinstance(self.message, dict):
            return f"Invalid location data: {', '.join(f'{k}: {v}' for k, v in self.message.items())}"
        elif isinstance(self.message, list):
            return f"Invalid location data: {', '.join(str(m) for m in self.message)}"
        return super().__str__()
