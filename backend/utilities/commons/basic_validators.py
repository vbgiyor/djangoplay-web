import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

_USERNAME_RE = re.compile(r"^[A-Za-z0-9]+$")


def is_valid_username(value: str) -> bool:
    if not isinstance(value, str):
        return False
    value = value.strip()
    return bool(value and _USERNAME_RE.fullmatch(value))


def is_valid_email(value: str) -> bool:
    if not isinstance(value, str):
        return False
    value = value.strip()
    if not value:
        return False
    try:
        validate_email(value)
        return True
    except ValidationError:
        return False
