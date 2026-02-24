import json
import os
from functools import lru_cache

from django.core.exceptions import ValidationError

# Immutable constant
PUBLIC_DOMAINS = (
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
)

VALID_DOMAINS_FILE_PATH = os.path.join(
    os.path.dirname(__file__),
    "valid_domains.json",
)


def _load_domains_from_file():
    """
    Read domains from JSON file safely.
    No side effects.
    """
    if not os.path.exists(VALID_DOMAINS_FILE_PATH):
        return []

    with open(VALID_DOMAINS_FILE_PATH, "r") as file:
        data = json.load(file)
        return data.get("valid_domains", [])


@lru_cache(maxsize=1)
def get_valid_domains():
    """
    Returns stable, deduplicated allowed domains.
    Cached for performance.
    """
    file_domains = _load_domains_from_file()

    # Preserve order + remove duplicates
    combined = list(dict.fromkeys(file_domains + list(PUBLIC_DOMAINS)))

    return combined


def save_valid_domains(new_domains):
    """
    Explicitly update JSON file.
    Clears cache after update.
    """
    unique = list(dict.fromkeys(new_domains))

    with open(VALID_DOMAINS_FILE_PATH, "w") as file:
        json.dump({"valid_domains": unique}, file, indent=4)

    # Refresh cache
    get_valid_domains.cache_clear()


def validate_domain(value):
    """
    Validator for email/domain field.
    """
    domain = value.split("@")[-1] if "@" in value else value

    if domain not in get_valid_domains():
        raise ValidationError(
            f"The domain '{domain}' is not allowed. Please use a valid domain."
        )

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
