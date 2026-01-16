# users/adapters/login/redirects.py

import logging

from allauth.account.utils import get_request_param
from django.conf import settings
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

logger = logging.getLogger(__name__)


class LoginRedirectHelper:

    """
    ============================================================================
    SAFE LOGIN REDIRECT HELPER
    ----------------------------------------------------------------------------
    Extracted from CustomAccountAdapter to keep redirect logic DRY.

    Responsibilities:
        • Resolve and validate "next" URL parameters
        • Fallback to console dashboard when not provided
        • Ensure host validation respects Django's ALLOWED_HOSTS +
          the active request host
    ============================================================================
    """

    DEFAULT_REDIRECT = "console_dashboard"

    @staticmethod
    def resolve_next_url(request):
        """
        Determine a safe next-URL, or return None if invalid.
        """
        next_url = get_request_param(request, "next")
        logger.debug("LoginRedirectHelper.resolve_next_url: raw next=%r", next_url)

        if next_url and isinstance(next_url, str):
            if next_url.startswith("/"):
                return next_url

        return None

    @staticmethod
    def get_safe_redirect_url(request):
        """
        Final redirect decision:
            • use safe next= param when allowed
            • otherwise fallback to DEFAULT_REDIRECT
        """
        next_url = LoginRedirectHelper.resolve_next_url(request)

        if next_url and LoginRedirectHelper.is_safe_url(next_url, request):
            return next_url

        return reverse(LoginRedirectHelper.DEFAULT_REDIRECT)

    @staticmethod
    def is_safe_url(url, request):
        """
        Validate URL using Django's built-in security rules.
        """
        allowed = set(settings.ALLOWED_HOSTS or [])
        try:
            allowed.add(request.get_host())
        except Exception:
            pass

        return url_has_allowed_host_and_scheme(url, allowed_hosts=allowed)
