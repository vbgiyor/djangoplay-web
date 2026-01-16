import re


def validate_regex(regex: str) -> bool:
    """Validate regex string using re.compile"""
    try:
        re.compile(regex)
        return True
    except re.error:
        return False
