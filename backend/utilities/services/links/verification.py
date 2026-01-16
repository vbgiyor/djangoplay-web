# utilities/services/links/verification.py
from urllib.parse import urlencode

from django.urls import reverse
from users.services.signup_token_manager import SignupTokenManagerService
from utilities.admin.url_utils import get_site_base_url


def build_verification_url(member) -> str:
    """
    Create a signed verification URL using SignupTokenManagerService.
    """
    signup_request, status = SignupTokenManagerService.create_for_user(
        user=member.employee,
        request=None,
    )

    if status != "ok":
        raise RuntimeError(f"Unable to create verification token: {status}")

    base_url = get_site_base_url()
    path = reverse("frontend:account_verify")
    query = urlencode({"token": signup_request.token})

    return f"{base_url}{path}?{query}"
