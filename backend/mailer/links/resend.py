from django.urls import reverse
from django.utils.http import urlencode
from django.conf import settings


def build_resend_verification_url(email: str) -> str:
    """
    Builds absolute resend-verification URL for a given email.
    """
    query = urlencode({"email": email})
    path = reverse("frontend:accounts_resend_verification")
    return f"{settings.SITE_URL}{path}?{query}"
