import logging
import random
import re
from string import ascii_uppercase, digits

from django.core.exceptions import ValidationError
from locations.models.custom_country import CustomCountry

logger = logging.getLogger('utilities.utils')
logger.setLevel(logging.WARNING)  # Minimize logging overhead

class PostalCodeValidationError(ValidationError):

    """Custom exception for postal code validation errors."""

    pass

def get_country_config(country_code: str) -> tuple[bool, str | None, int | None]:
    """Retrieve postal code configuration for a country."""
    try:
        country = CustomCountry.objects.get(country_code=country_code.upper())
        postal_code_length = int(country.postal_code_length) if country.postal_code_length else None
        return country.has_postal_code, country.postal_code_regex, postal_code_length
    except CustomCountry.DoesNotExist:
        logger.warning(f"Country '{country_code}' not found.")
        raise PostalCodeValidationError(f"Country '{country_code}' not found.")

def validate_postal_code(postal_code: str | None, country_code: str, regex: str, postal_code_length: int | None) -> str | None:
    """
    Validate a postal code for a given country.

    Args:
        postal_code: The postal code to validate, or None.
        country_code: ISO country code (e.g., 'US', 'CA', 'NZ', 'GB').
        regex: Postal code regex pattern.
        postal_code_length: Maximum allowed length.

    Returns:
        Validated postal code, or None if not required.

    Raises:
        PostalCodeValidationError: If validation fails or country is invalid.

    """
    if not country_code:
        raise PostalCodeValidationError("Country code is required.")

    country_code = country_code.upper().strip()
    postal_code = postal_code.strip() if postal_code else None

    if not postal_code:
        raise PostalCodeValidationError(f"Postal code is required for country '{country_code}'.")

    if not regex:
        raise PostalCodeValidationError(f"No postal code regex defined for '{country_code}'.")

    try:
        if not re.match(regex, postal_code):
            raise PostalCodeValidationError(f"Invalid postal code format: '{postal_code}'")
        if postal_code_length and len(postal_code) > postal_code_length:
            raise PostalCodeValidationError(f"Postal code exceeds maximum length of {postal_code_length} for '{country_code}'")
        return postal_code
    except re.error as e:
        logger.error(f"Invalid regex pattern '{regex}': {e}")
        raise PostalCodeValidationError(f"Invalid regex pattern: {e}")

def generate_postal_code(country_code: str, config_cache: dict | None = None) -> str:
    """
    Generate a valid postal code for the specified country based on its regex and length.

    Args:
        country_code: ISO country code (e.g., 'NZ', 'US', 'CA', 'GB').
        config_cache: Optional dict to cache country config (has_postal_code, regex, postal_code_length).

    Returns:
        A valid postal code.

    Raises:
        PostalCodeValidationError: If generation fails or no regex is available.

    """
    country_code = country_code.upper()

    # Use cached config if provided, else query database
    if config_cache and country_code in config_cache:
        has_postal_code, regex, postal_code_length = config_cache[country_code]
    else:
        has_postal_code, regex, postal_code_length = get_country_config(country_code)
        if config_cache is not None:
            config_cache[country_code] = (has_postal_code, regex, postal_code_length)

    if not has_postal_code:
        raise PostalCodeValidationError(f"Postal codes are not supported for {country_code}")

    if not regex:
        raise PostalCodeValidationError(f"No postal code regex defined for {country_code}")

    # Handle fixed-format postal codes
    fixed_codes = {
        'AS': '96799', 'FK': 'FIQQ 1ZZ', 'GI': 'GX11 1AA', 'IO': 'BBND 1ZZ',
        'PN': 'PCRN 1ZZ', 'SH': 'STHL1ZZ', 'TC': 'TKCA 1ZZ', 'TD': 'TKCA 1ZZ',
        'PW': '96940', 'NR': 'NRU68'
    }
    if country_code in fixed_codes:
        postal_code = fixed_codes[country_code]
        return validate_postal_code(postal_code, country_code, regex, postal_code_length)

    # Handle numeric postal codes with optional extensions
    numeric_with_optional = {
        'US': (r'^\d{5}(-\d{4})?$', 5, lambda: ''.join(random.choice(digits) for _ in range(5))),
        'PR': (r'^00[679]\d{2}(?:-\d{4})?$', 5, lambda: '00' + random.choice('679') + ''.join(random.choice(digits) for _ in range(2))),
        'VI': (r'^008\d{2}(?:-\d{4})?$', 5, lambda: '008' + ''.join(random.choice(digits) for _ in range(2)))
    }
    if country_code in numeric_with_optional and (postal_code_length is None or postal_code_length == 5):
        pattern, _, generator = numeric_with_optional[country_code]
        if regex == pattern:
            postal_code = generator()
            return validate_postal_code(postal_code, country_code, regex, postal_code_length)

    # Handle simple numeric postal codes
    numeric_patterns = [
        (r'^\d{3}$', r'^(\d{3})$', 3), (r'^\d{4}$', r'^(\d{4})$', 4),
        (r'^\d{5}$', r'^(\d{5})$', 5), (r'^\d{6}$', r'^(\d{6})$', 6),
        (r'^\d{7}$', r'^(\d{7})$', 7), (r'^\d{10}$', r'^(\d{10})$', 10)
    ]
    for pattern, alt_pattern, length in numeric_patterns:
        if regex in (pattern, alt_pattern) and (postal_code_length is None or postal_code_length >= length):
            length = min(length, postal_code_length) if postal_code_length else length
            postal_code = ''.join(random.choice(digits) for _ in range(length))
            return validate_postal_code(postal_code, country_code, regex, postal_code_length)

    # Handle other common patterns
    common_patterns = {
        'CA': (r'^([ABCEGHJKLMNPRSTVXY]\d[ABCEGHJKLMNPRSTVWXYZ]) ?(\d[ABCEGHJKLMNPRSTVWXYZ]\d)$',
               lambda: random.choice('ABCEGHJKLMNPRSTVXY') + random.choice(digits) + random.choice('ABCEGHJKLMNPRSTVWXYZ') + ' ' + random.choice(digits) + random.choice('ABCEGHJKLMNPRSTVWXYZ') + random.choice(digits)),
        'NL': (r'^(\d{4}\s?[a-zA-Z]{2})$', lambda: ''.join(random.choice(digits) for _ in range(4)) + ' ' + ''.join(random.choice(ascii_uppercase) for _ in range(2))),
        'BR': (r'^\d{5}-\d{3}$', lambda: ''.join(random.choice(digits) for _ in range(5)) + '-' + ''.join(random.choice(digits) for _ in range(3))),
        'JP': (r'^\d{3}-\d{4}$', lambda: ''.join(random.choice(digits) for _ in range(3)) + '-' + ''.join(random.choice(digits) for _ in range(4))),
        'PL': (r'^\d{2}-\d{3}$', lambda: ''.join(random.choice(digits) for _ in range(2)) + '-' + ''.join(random.choice(digits) for _ in range(3))),
        'AU': (r'^\d{4}$', lambda: ''.join(random.choice(digits) for _ in range(4))),
        'DE': (r'^\d{5}$', lambda: ''.join(random.choice(digits) for _ in range(5))),
        'FR': (r'^(\d{5})$', lambda: ''.join(random.choice(digits) for _ in range(5))),
        'IN': (r'^(\d{6})$', lambda: ''.join(random.choice(digits) for _ in range(6))),
        'NZ': (r'^\d{4}$', lambda: ''.join(random.choice(digits) for _ in range(4)))
    }
    if country_code in common_patterns:
        pattern, generator = common_patterns[country_code]
        if regex == pattern and (postal_code_length is None or postal_code_length >= len(generator())):
            postal_code = generator()
            return validate_postal_code(postal_code, country_code, regex, postal_code_length)

    # Fallback to regex parsing for complex patterns
    try:
        postal_code = _generate_from_regex(regex, postal_code_length)
        return validate_postal_code(postal_code, country_code, regex, postal_code_length)
    except PostalCodeValidationError as e:
        # Final fallback: generate numeric code if pattern suggests digits
        if postal_code_length and re.match(r'^\d{\d+}(?:\(\d+\))?(\-\d+)?$', regex):
            postal_code = ''.join(random.choice(digits) for _ in range(postal_code_length))
            return validate_postal_code(postal_code, country_code, regex, postal_code_length)
        raise PostalCodeValidationError(f"Failed to generate valid postal code for {country_code}: {e}")

def _generate_from_regex(regex: str, postal_code_length: int | None = None) -> str:
    """
    Generate a postal code based on the provided regex pattern and length constraint.

    Args:
        regex: Postal code regex pattern.
        postal_code_length: Maximum allowed length for the postal code.

    Returns:
        Generated postal code.

    Raises:
        PostalCodeValidationError: If generation fails due to invalid regex or length.

    """
    try:
        regex = regex.strip('^$')
        result = []
        current_length = 0
        i = 0
        while i < len(regex):
            if postal_code_length is not None and current_length >= postal_code_length:
                break

            char = regex[i]

            if char in ascii_uppercase or char in digits or char in ' -':
                result.append(char)
                current_length += 1
                i += 1
                continue

            if char == '\\':
                if i + 1 < len(regex):
                    next_char = regex[i + 1]
                    if next_char == 'd':
                        result.append(random.choice(digits))
                        current_length += 1
                        i += 2
                        continue
                    elif next_char == 's':
                        result.append(' ')
                        current_length += 1
                        i += 2
                        continue
                raise PostalCodeValidationError(f"Invalid escape sequence at position {i}")

            if char == '[':
                j = i + 1
                char_class = []
                while j < len(regex) and regex[j] != ']':
                    char_class.append(regex[j])
                    j += 1
                if j >= len(regex):
                    raise PostalCodeValidationError(f"Unclosed bracket at position {i}")
                char_class = ''.join(char_class)
                if char_class == 'A-Z':
                    result.append(random.choice(ascii_uppercase))
                elif char_class == '0-9':
                    result.append(random.choice(digits))
                elif char_class == 'A-Za-z':
                    result.append(random.choice(ascii_uppercase))
                elif 'A-Ha-hJ-Yj-y' in char_class:
                    valid_letters = [c for c in ascii_uppercase if c not in 'IJ']
                    result.append(random.choice(valid_letters))
                elif char_class == 'Aa':
                    result.append('A')
                else:
                    result.append(random.choice(char_class))
                current_length += 1
                i = j + 1
                continue

            if char == '{':
                j = i + 1
                num_str = ''
                while j < len(regex) and regex[j].isdigit():
                    num_str += regex[j]
                    j += 1
                if j < len(regex) and regex[j] == '}':
                    count = int(num_str)
                    if postal_code_length is not None:
                        count = min(count, postal_code_length - current_length)
                    if result and count > 0:
                        result[-1] = result[-1] * count
                        current_length += count - 1
                    i = j + 1
                    continue
                elif j < len(regex) and regex[j] == ',':
                    j += 1
                    max_num = ''
                    while j < len(regex) and regex[j].isdigit():
                        max_num += regex[j]
                        j += 1
                    if j < len(regex) and regex[j] == '}':
                        min_count = int(num_str)
                        max_count = int(max_num)
                        if postal_code_length is not None:
                            max_count = min(max_count, postal_code_length - current_length)
                        count = random.randint(min_count, max_count)
                        if result and count > 0:
                            result[-1] = result[-1] * count
                            current_length += count - 1
                        i = j + 1
                        continue
                raise PostalCodeValidationError(f"Invalid quantifier at position {i}")

            if char == '?' and i > 0:
                if result and random.choice([True, False]) and current_length < postal_code_length:
                    result.pop()
                    current_length -= 1
                i += 1
                continue

            if char == '|' and i > 0 and regex[i - 1] != '\\':
                alternations = []
                current = []
                paren_count = 0
                j = 0
                while j < len(regex):
                    if regex[j] == '(':
                        paren_count += 1
                    elif regex[j] == ')':
                        paren_count -= 1
                    elif regex[j] == '|' and paren_count == 0:
                        alternations.append(''.join(current))
                        current = []
                        j += 1
                        continue
                    current.append(regex[j])
                    j += 1
                if current:
                    alternations.append(''.join(current))
                valid_alternations = [
                    alt for alt in alternations
                    if postal_code_length is None or len(alt.replace('\\d', '0').replace('\\s', ' ').replace('[A-Z]', 'A')) <= postal_code_length
                ]
                if not valid_alternations:
                    raise PostalCodeValidationError(f"No valid alternations for length {postal_code_length}")
                selected = random.choice(valid_alternations)
                return _generate_from_regex(selected, postal_code_length)

            if char == '(':
                j = i + 1
                paren_count = 1
                group = []
                while j < len(regex) and paren_count > 0:
                    if regex[j] == '(':
                        paren_count += 1
                    elif regex[j] == ')':
                        paren_count -= 1
                    if paren_count > 0:
                        group.append(regex[j])
                    j += 1
                if paren_count != 0:
                    raise PostalCodeValidationError(f"Unclosed parenthesis at position {i}")
                group_str = ''.join(group)
                parsed_group = _generate_from_regex(group_str, postal_code_length - current_length if postal_code_length else None)
                group_length = len(parsed_group)
                if postal_code_length is not None and current_length + group_length <= postal_code_length:
                    result.append(parsed_group)
                    current_length += group_length
                elif postal_code_length is not None:
                    result.append(parsed_group[:postal_code_length - current_length])
                    current_length = postal_code_length
                else:
                    result.append(parsed_group)
                    current_length += group_length
                i = j + 1
                continue

            i += 1

        generated = ''.join(result)
        if postal_code_length is not None and len(generated) > postal_code_length:
            generated = generated[:postal_code_length]
        if not generated:
            raise PostalCodeValidationError("Generated empty postal code")
        return generated
    except Exception as e:
        raise PostalCodeValidationError(f"Failed to generate postal code from regex: {e}")


# import re
# import random
# import logging
# from django.core.exceptions import ValidationError
# from locations.models.custom_country import CustomCountry
# from string import ascii_uppercase, digits

# logger = logging.getLogger(__name__)

# class PostalCodeValidationError(ValidationError):
#     """Custom exception for postal code validation errors."""
#     pass

# def get_country_config(country_code: str) -> tuple[bool, str | None, int | None]:
#     """Retrieve postal code configuration for a country."""
#     try:
#         country = CustomCountry.objects.get(country_code=country_code.upper())
#         postal_code_length = int(country.postal_code_length) if country.postal_code_length else None
#         return country.has_postal_code, country.postal_code_regex, postal_code_length
#     except CustomCountry.DoesNotExist:
#         logger.warning(f"Country '{country_code}' not found.")
#         raise PostalCodeValidationError(f"Country '{country_code}' not found.")

# def validate_postal_code(postal_code: str | None, country_code: str, custom_regex: str | None = None) -> str | None:
#     """
#     Validate a postal code for a given country.

#     Args:
#         postal_code: The postal code to validate, or None.
#         country_code: ISO country code (e.g., 'IN', 'US', 'CA', 'NZ', 'GB').
#         custom_regex: Optional custom regex to override default.

#     Returns:
#         Validated postal code, or None if not required.

#     Raises:
#         PostalCodeValidationError: If validation fails or country is invalid.
#     """
#     if not country_code:
#         raise PostalCodeValidationError("Country code is required.")

#     country_code = country_code.upper().strip()
#     postal_code = postal_code.strip() if postal_code else None
#     logger.debug(f"Validating postal code: '{postal_code}' for country: '{country_code}'")

#     has_postal_code, regex, postal_code_length = get_country_config(country_code)

#     if not has_postal_code:
#         if postal_code:
#             raise PostalCodeValidationError(f"Country '{country_code}' does not use postal codes.")
#         return None

#     if not postal_code:
#         raise PostalCodeValidationError(f"Postal code is required for country '{country_code}'.")

#     regex = custom_regex or regex
#     if not regex:
#         raise PostalCodeValidationError(f"No postal code regex defined for '{country_code}'.")

#     try:
#         if not re.match(regex, postal_code):
#             logger.debug(f"Postal code '{postal_code}' failed regex validation: {regex}")
#             raise PostalCodeValidationError(f"Invalid postal code format: '{postal_code}'")
#         if postal_code_length and len(postal_code) > postal_code_length:
#             logger.debug(f"Postal code '{postal_code}' exceeds length {postal_code_length}")
#             raise PostalCodeValidationError(f"Postal code exceeds maximum length of {postal_code_length} for '{country_code}'")
#         logger.debug(f"Postal code '{postal_code}' validated successfully.")
#         return postal_code
#     except re.error as e:
#         logger.error(f"Invalid regex pattern '{regex}': {e}")
#         raise PostalCodeValidationError(f"Invalid regex pattern: {e}")

# def generate_postal_code(country_code: str) -> str:
#     """
#     Generate a valid postal code for the specified country based on its regex and length.

#     Args:
#         country_code: ISO country code (e.g., 'NZ', 'US', 'CA', 'GB').

#     Returns:
#         A valid postal code.

#     Raises:
#         PostalCodeValidationError: If generation fails or no regex is available.
#     """
#     country_code = country_code.upper()
#     has_postal_code, regex, postal_code_length = get_country_config(country_code)

#     if not has_postal_code:
#         raise PostalCodeValidationError(f"Postal codes are not supported for {country_code}")

#     if not regex:
#         raise PostalCodeValidationError(f"No postal code regex defined for {country_code}")

#     # Handle fixed-format postal codes
#     fixed_codes = {
#         'AS': '96799', 'FK': 'FIQQ 1ZZ', 'GI': 'GX11 1AA', 'IO': 'BBND 1ZZ',
#         'PN': 'PCRN 1ZZ', 'SH': 'STHL1ZZ', 'TC': 'TKCA 1ZZ', 'TD': 'TKCA 1ZZ',
#         'PW': '96940', 'NR': 'NRU68'
#     }
#     if country_code in fixed_codes:
#         postal_code = fixed_codes[country_code]
#         try:
#             validated_postal_code = validate_postal_code(postal_code, country_code, regex)
#             logger.debug(f"Generated fixed postal code '{validated_postal_code}' for {country_code}")
#             return validated_postal_code
#         except PostalCodeValidationError as e:
#             logger.debug(f"Fixed code generation failed for {country_code}: {e}")
#             raise

#     # Handle numeric postal codes with optional extensions (e.g., US, PR, VI)
#     numeric_with_optional = {
#         'US': (r'^\d{5}(-\d{4})?$', 5, lambda: ''.join(random.choice(digits) for _ in range(5))),
#         'PR': (r'^00[679]\d{2}(?:-\d{4})?$', 5, lambda: '00' + random.choice('679') + ''.join(random.choice(digits) for _ in range(2))),
#         'VI': (r'^008\d{2}(?:-\d{4})?$', 5, lambda: '008' + ''.join(random.choice(digits) for _ in range(2)))
#     }
#     if country_code in numeric_with_optional and (postal_code_length is None or postal_code_length == 5):
#         pattern, _, generator = numeric_with_optional[country_code]
#         if regex == pattern:
#             postal_code = generator()
#             try:
#                 validated_postal_code = validate_postal_code(postal_code, country_code, regex)
#                 logger.debug(f"Generated numeric postal code '{validated_postal_code}' for {country_code}")
#                 return validated_postal_code
#             except PostalCodeValidationError as e:
#                 logger.debug(f"Numeric generation failed for {country_code}: {e}")

#     # Handle simple numeric postal codes
#     numeric_patterns = [
#         (r'^\d{3}$', r'^(\d{3})$', 3), (r'^\d{4}$', r'^(\d{4})$', 4),
#         (r'^\d{5}$', r'^(\d{5})$', 5), (r'^\d{6}$', r'^(\d{6})$', 6),
#         (r'^\d{7}$', r'^(\d{7})$', 7), (r'^\d{10}$', r'^(\d{10})$', 10)
#     ]
#     for pattern, alt_pattern, length in numeric_patterns:
#         if regex in (pattern, alt_pattern) and (postal_code_length is None or postal_code_length >= length):
#             length = min(length, postal_code_length) if postal_code_length else length
#             postal_code = ''.join(random.choice(digits) for _ in range(length))
#             try:
#                 validated_postal_code = validate_postal_code(postal_code, country_code, regex)
#                 logger.debug(f"Generated numeric postal code '{validated_postal_code}' for {country_code}")
#                 return validated_postal_code
#             except PostalCodeValidationError as e:
#                 logger.debug(f"Numeric generation failed for {country_code}: {e}")

#     max_attempts = 5
#     for attempt in range(max_attempts):
#         try:
#             # Generate postal code based on regex
#             postal_code = _generate_from_regex(regex, postal_code_length)
#             # Validate using the same regex
#             validated_postal_code = validate_postal_code(postal_code, country_code, regex)
#             logger.debug(f"Generated valid postal code '{validated_postal_code}' for {country_code}")
#             return validated_postal_code
#         except PostalCodeValidationError as e:
#             logger.debug(f"Attempt {attempt + 1} failed for {country_code}: {e}")
#             if attempt == max_attempts - 1:
#                 # Fallback for patterns not caught above
#                 if postal_code_length:
#                     # Try generating a simple numeric code if regex suggests digits
#                     if re.match(r'^\d{\d+}(?:\(\d+\))?(\-\d+)?$', regex):
#                         postal_code = ''.join(random.choice(digits) for _ in range(postal_code_length))
#                         try:
#                             validated_postal_code = validate_postal_code(postal_code, country_code, regex)
#                             logger.debug(f"Fallback generated valid postal code '{validated_postal_code}' for {country_code}")
#                             return validated_postal_code
#                         except PostalCodeValidationError as fallback_error:
#                             logger.debug(f"Fallback failed for {country_code}: {fallback_error}")
#                 raise PostalCodeValidationError(f"Failed to generate valid postal code for {country_code} after {max_attempts} attempts")

# def _generate_from_regex(regex: str, postal_code_length: int | None = None) -> str:
#     """
#     Generate a postal code based on the provided regex pattern and length constraint.

#     Args:
#         regex: Postal code regex pattern.
#         postal_code_length: Maximum allowed length for the postal code.

#     Returns:
#         Generated postal code.

#     Raises:
#         PostalCodeValidationError: If generation fails due to invalid regex or length.
#     """
#     try:
#         # Remove anchors (^ and $) for generation
#         regex = regex.strip('^$')
#         logger.debug(f"Parsing regex: {regex} with max length: {postal_code_length}")

#         def parse_regex(pattern: str, current_length: int = 0) -> str:
#             """Parse regex pattern and generate a valid string."""
#             result = []
#             i = 0
#             while i < len(pattern):
#                 if postal_code_length is not None and current_length >= postal_code_length:
#                     break

#                 char = pattern[i]

#                 # Handle literal characters
#                 if char in ascii_uppercase or char in digits or char in ' -':
#                     result.append(char)
#                     current_length += 1
#                     i += 1
#                     continue

#                 # Handle escaped sequences
#                 if char == '\\':
#                     if i + 1 < len(pattern):
#                         next_char = pattern[i + 1]
#                         if next_char == 'd':
#                             result.append(random.choice(digits))
#                             current_length += 1
#                             i += 2
#                             continue
#                         elif next_char == 's':
#                             result.append(' ')
#                             current_length += 1
#                             i += 2
#                             continue
#                     raise PostalCodeValidationError(f"Invalid escape sequence at position {i}")

#                 # Handle character classes
#                 if char == '[':
#                     j = i + 1
#                     char_class = []
#                     while j < len(pattern) and pattern[j] != ']':
#                         char_class.append(pattern[j])
#                         j += 1
#                     if j >= len(pattern):
#                         raise PostalCodeValidationError(f"Unclosed bracket at position {i}")
#                     char_class = ''.join(char_class)
#                     if char_class == 'A-Z':
#                         result.append(random.choice(ascii_uppercase))
#                     elif char_class == '0-9':
#                         result.append(random.choice(digits))
#                     elif char_class == 'A-Za-z':
#                         result.append(random.choice(ascii_uppercase))
#                     elif 'A-Ha-hJ-Yj-y' in char_class:
#                         valid_letters = [c for c in ascii_uppercase if c not in 'IJ']
#                         result.append(random.choice(valid_letters))
#                     elif char_class == 'Aa':
#                         result.append('A')
#                     else:
#                         result.append(random.choice(char_class))
#                     current_length += 1
#                     i = j + 1
#                     continue

#                 # Handle quantifiers
#                 if char == '{':
#                     j = i + 1
#                     num_str = ''
#                     while j < len(pattern) and pattern[j].isdigit():
#                         num_str += pattern[j]
#                         j += 1
#                     if j < len(pattern) and pattern[j] == '}':
#                         count = int(num_str)
#                         if postal_code_length is not None:
#                             count = min(count, postal_code_length - current_length)
#                         if result and count > 0:
#                             result[-1] = result[-1] * count
#                             current_length += count - 1
#                         i = j + 1
#                         continue
#                     elif j < len(pattern) and pattern[j] == ',':
#                         j += 1
#                         max_num = ''
#                         while j < len(pattern) and pattern[j].isdigit():
#                             max_num += pattern[j]
#                             j += 1
#                         if j < len(pattern) and pattern[j] == '}':
#                             min_count = int(num_str)
#                             max_count = int(max_num)
#                             if postal_code_length is not None:
#                                 max_count = min(max_count, postal_code_length - current_length)
#                             count = random.randint(min_count, max_count)
#                             if result and count > 0:
#                                 result[-1] = result[-1] * count
#                                 current_length += count - 1
#                             i = j + 1
#                             continue
#                     raise PostalCodeValidationError(f"Invalid quantifier at position {i}")
#                 elif char == '?':
#                     if result and random.choice([True, False]) and current_length < postal_code_length:
#                         result.pop()
#                         current_length -= 1
#                     i += 1
#                     continue

#                 # Handle alternations
#                 if char == '|' and i > 0 and pattern[i - 1] != '\\':
#                     alternations = split_alternations(pattern)
#                     valid_alternations = [
#                         alt for alt in alternations
#                         if postal_code_length is None or estimate_pattern_length(alt) <= postal_code_length
#                     ]
#                     if not valid_alternations:
#                         raise PostalCodeValidationError(f"No valid alternations for length {postal_code_length}")
#                     selected = random.choice(valid_alternations)
#                     parsed = parse_regex(selected, current_length)
#                     return parsed

#                 # Handle groups
#                 if char == '(':
#                     j = i + 1
#                     paren_count = 1
#                     group = []
#                     while j < len(pattern) and paren_count > 0:
#                         if pattern[j] == '(':
#                             paren_count += 1
#                         elif pattern[j] == ')':
#                             paren_count -= 1
#                         if paren_count > 0:
#                             group.append(pattern[j])
#                         j += 1
#                     if paren_count != 0:
#                         raise PostalCodeValidationError(f"Unclosed parenthesis at position {i}")
#                     group_str = ''.join(group)
#                     parsed_group = parse_regex(group_str, current_length)
#                     group_length = len(parsed_group)
#                     if postal_code_length is not None and current_length + group_length <= postal_code_length:
#                         result.append(parsed_group)
#                         current_length += group_length
#                     elif postal_code_length is not None:
#                         result.append(parsed_group[:postal_code_length - current_length])
#                         current_length = postal_code_length
#                     else:
#                         result.append(parsed_group)
#                         current_length += group_length
#                     i = j + 1
#                     continue

#                 i += 1

#             generated = ''.join(result)
#             if postal_code_length is not None and len(generated) > postal_code_length:
#                 generated = generated[:postal_code_length]
#             return generated

#         def estimate_pattern_length(pattern: str) -> int:
#             """Estimate the minimum length of a regex pattern."""
#             length = 0
#             i = 0
#             while i < len(pattern):
#                 if pattern[i] in ascii_uppercase or pattern[i] in digits or pattern[i] in ' -':
#                     length += 1
#                     i += 1
#                     continue
#                 if pattern[i] == '\\':
#                     if i + 1 < len(pattern) and pattern[i + 1] in 'ds':
#                         length += 1
#                         i += 2
#                         continue
#                 if pattern[i] == '[':
#                     i += 1
#                     while i < len(pattern) and pattern[i] != ']':
#                         i += 1
#                     length += 1
#                     i += 1
#                     continue
#                 if pattern[i] == '{':
#                     j = i + 1
#                     num_str = ''
#                     while j < len(pattern) and pattern[j].isdigit():
#                         num_str += pattern[j]
#                         j += 1
#                     if j < len(pattern) and pattern[j] == '}':
#                         length += int(num_str) - 1
#                         i = j + 1
#                         continue
#                     elif j < len(pattern) and pattern[j] == ',':
#                         j += 1
#                         while j < len(pattern) and pattern[j].isdigit():
#                             j += 1
#                         if j < len(pattern) and pattern[j] == '}':
#                             length += int(num_str) - 1
#                             i = j + 1
#                             continue
#                     i += 1
#                     continue
#                 if pattern[i] == '(':
#                     j = i + 1
#                     paren_count = 1
#                     group = []
#                     while j < len(pattern) and paren_count > 0:
#                         if pattern[j] == '(':
#                             paren_count += 1
#                         elif pattern[j] == ')':
#                             paren_count -= 1
#                         if paren_count > 0:
#                             group.append(pattern[j])
#                         j += 1
#                     length += estimate_pattern_length(''.join(group))
#                     i = j + 1
#                     continue
#                 if pattern[i] == '?' and i > 0:
#                     length = max(0, length - 1)
#                     i += 1
#                     continue
#                 i += 1
#             return length

#         def split_alternations(regex_str: str) -> list[str]:
#             """Split regex by top-level alternations (|)."""
#             parts = []
#             current = []
#             paren_count = 0
#             i = 0
#             while i < len(regex_str):
#                 if regex_str[i] == '(':
#                     paren_count += 1
#                 elif regex_str[i] == ')':
#                     paren_count -= 1
#                 elif regex_str[i] == '|' and paren_count == 0:
#                     parts.append(''.join(current))
#                     current = []
#                     i += 1
#                     continue
#                 current.append(regex_str[i])
#                 i += 1
#             if current:
#                 parts.append(''.join(current))
#             return parts

#         # Generate postal code
#         generated = parse_regex(regex)
#         if not generated:
#             raise PostalCodeValidationError("Generated empty postal code")
#         if postal_code_length is not None and len(generated) > postal_code_length:
#             generated = generated[:postal_code_length]
#         logger.debug(f"Generated postal code: {generated}")
#         return generated
#     except Exception as e:
#         logger.error(f"Error generating postal code from regex: {e}")
#         raise PostalCodeValidationError(f"Failed to generate postal code from regex: {e}")
