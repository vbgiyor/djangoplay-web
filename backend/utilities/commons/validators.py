import json
import os
import re

from django.core.exceptions import ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email

# Username: ONLY letters and digits, at least 1 char, nothing else allowed
_USERNAME_RE = re.compile(r"^[A-Za-z0-9]+$")


def is_valid_username(value: str) -> bool:
    """
    Username must be non-empty and strictly alphanumeric (A–Z, a–z, 0–9).
    No spaces, no underscores, no symbols.
    """
    if not isinstance(value, str):
        return False

    value = value.strip()
    if not value:
        return False

    # fullmatch enforces that the WHOLE string matches, not just a part of it.
    return bool(_USERNAME_RE.fullmatch(value))


def is_valid_email(value: str) -> bool:
    """
    Validate email using Django's validate_email.
    """
    if not isinstance(value, str):
        return False

    value = value.strip()
    if not value:
        return False

    try:
        validate_email(value)
        return True
    except DjangoValidationError:
        return False


# Define a list of public domains
PUBLIC_DOMAINS = [
    'gmail.com',
    'yahoo.com',
    'outlook.com',
    'hotmail.com',
]

# Path to the valid_domains.json file
VALID_DOMAINS_FILE_PATH = os.path.join(os.path.dirname(__file__), 'valid_domains.json')

# Load the valid domains from the JSON file
def load_valid_domains():
    if os.path.exists(VALID_DOMAINS_FILE_PATH):
        with open(VALID_DOMAINS_FILE_PATH, 'r') as file:
            data = json.load(file)
            return data.get('valid_domains', [])
    return []

# Save the updated list of valid domains to the JSON file
def save_valid_domains(valid_domains):
    with open(VALID_DOMAINS_FILE_PATH, 'w') as file:
        json.dump({"valid_domains": valid_domains}, file, indent=4)

# Combine the valid domains from the file with the public domains and ensure uniqueness
def update_valid_domains():
    valid_domains = load_valid_domains()

    # Append public domains to the list and remove duplicates
    combined_domains = list(set(valid_domains + PUBLIC_DOMAINS))

    # Save the updated valid domains list back to the JSON file
    save_valid_domains(combined_domains)

    return combined_domains

# Load the final valid domains (combining public domains with any existing ones)
VALID_DOMAINS = update_valid_domains()

def validate_domain(value):
    """
    Validator that checks if the domain is in the valid domains loaded from the JSON file.
    """
    domain = value.split('@')[-1] if '@' in value else value

    # Check if the domain is in the list of valid domains
    if domain not in VALID_DOMAINS:
        raise ValidationError(f"The domain '{domain}' is not allowed. Please use a valid domain.")
    

# import json
# import os
# from functools import lru_cache
# from django.core.exceptions import ValidationError

# # Public domains (constant, never modified)
# PUBLIC_DOMAINS = (
#     "gmail.com",
#     "yahoo.com",
#     "outlook.com",
#     "hotmail.com",
# )

# VALID_DOMAINS_FILE_PATH = os.path.join(
#     os.path.dirname(__file__),
#     "valid_domains.json"
# )


# def load_valid_domains_from_file():
#     """Read domains from JSON file safely."""
#     if not os.path.exists(VALID_DOMAINS_FILE_PATH):
#         return []

#     with open(VALID_DOMAINS_FILE_PATH, "r") as file:
#         data = json.load(file)
#         return data.get("valid_domains", [])


# @lru_cache(maxsize=1)
# def get_valid_domains():
#     """
#     Returns a stable, deduplicated list of valid domains.
#     Cached for performance.
#     """
#     file_domains = load_valid_domains_from_file()

#     # Preserve order while removing duplicates
#     combined = list(dict.fromkeys(file_domains + list(PUBLIC_DOMAINS)))

#     return combined


# def save_valid_domains(new_domains):
#     """
#     Explicitly update the JSON file.
#     Clears cache after update.
#     """
#     unique_domains = list(dict.fromkeys(new_domains))

#     with open(VALID_DOMAINS_FILE_PATH, "w") as file:
#         json.dump({"valid_domains": unique_domains}, file, indent=4)

#     # Clear cache so next call reloads fresh data
#     get_valid_domains.cache_clear()


# def validate_domain(value):
#     """
#     Validator that checks if the domain is allowed.
#     """
#     domain = value.split("@")[-1] if "@" in value else value

#     if domain not in get_valid_domains():
#         raise ValidationError(
#             f"The domain '{domain}' is not allowed. Please use a valid domain."
#         )