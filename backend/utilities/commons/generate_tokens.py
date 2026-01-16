import secrets
import string

DEFAULT_TOKEN_LENGTH = 64


def generate_secure_token(length: int = DEFAULT_TOKEN_LENGTH, prefix: str = "") -> str:
    """
    Generate a cryptographically secure opaque token.

    - Uses URL-safe characters
    - Length applies to the RANDOM portion only (prefix excluded)
    - Final token = prefix + random_string

    Example:
        generate_secure_token(prefix="vrf_")
        → "vrf_p3k8...<60 more chars>"

    """
    alphabet = string.ascii_letters + string.digits
    random_part = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}{random_part}"
