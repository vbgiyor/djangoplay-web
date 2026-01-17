import logging

from django.conf import settings

from users.adapters.context.support import SupportContextProvider
from users.adapters.login.redirects import LoginRedirectHelper
from users.adapters.login.validation import LoginValidationHelper

logger = logging.getLogger(__name__)


class BaseAdapter:

    """
    Shared utilities for all adapters (account + social).
    This class does NOT override allauth hooks.
    It only provides reusable helpers.

    Do NOT put domain logic here.
    """

    # ---------------------------------------------------------
    # Basic helpers
    # ---------------------------------------------------------
    def get_support_context(self) -> dict:
        return SupportContextProvider.build()

    def get_redirect_resolver(self) -> LoginRedirectHelper:
        return LoginRedirectHelper()

    def get_login_validator(self) -> LoginValidationHelper:
        return LoginValidationHelper()

    # ---------------------------------------------------------
    # Convenience wrappers
    # ---------------------------------------------------------
    def safe_redirect(self, url: str) -> str:
        rr = self.get_redirect_resolver()
        return rr.resolve(url)

    def validate_login(self, user):
        """
        Wrapper around UnifiedLoginService with consistent logging.
        """
        validator = self.get_login_validator()
        result = validator.validate(user)

        if not result.ok:
            logger.info(
                "BaseAdapter.login rejected: %s → reason=%s",
                getattr(user, "email", None),
                result.reason,
            )

        return result

    # ---------------------------------------------------------
    # Email helpers
    # ---------------------------------------------------------
    def send_template_email(
        self,
        template_prefix: str,
        to: str,
        context: dict,
        user=None,
    ):
        """
        Unified email send entrypoint for all adapters.
        """
        engine = self.get_email_engine()
        return engine.send(
            prefix=template_prefix,
            email=to,
            context=context,
            user=user,
        )

    # ---------------------------------------------------------
    # Default domain-agnostic messages
    # ---------------------------------------------------------
    def get_site_name(self) -> str:
        return getattr(settings, "SITE_NAME", "DjangoPlay")
