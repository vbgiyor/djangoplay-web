from urllib.parse import urlencode

from django.urls import reverse
from utilities.admin.url_utils import get_site_base_url


def build_verification_url(*, member, signup_request) -> str:
    """
    Create a signed verification URL.
    Token ownership is enforced here.
    """
    if not signup_request or not signup_request.token:
        raise RuntimeError("Signup request token missing")

    base_url = get_site_base_url()
    path = reverse("frontend:account_verify")
    query = urlencode({"token": signup_request.token})

    return f"{base_url}{path}?{query}"
