import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoginValidationResult:
    ok: bool
    reason: str | None = None


class UnifiedLoginService:

    """
    Single source of truth for validating whether a user can log in.

    Enforces STRICT production rules:
    - User must be active
    - User must NOT be soft-deleted
    - User must be verified (email/SAML/SSO)
    - User.must have employment_status == ACTV
    """

    @staticmethod
    def map_reason_to_message(reason: str) -> str:
        mapping = {
            "USER_NOT_FOUND": "User account does not exist.",
            "ACCOUNT_DELETED": "Your account has been deleted.",
            "ACCOUNT_INACTIVE": "Your account is inactive. Contact administrator.",
            "EMAIL_NOT_VERIFIED": "Email verification pending. Please verify your email.",
            "EMPLOYMENT_NOT_ACTIVE": "Your employment status is inactive. Contact administrator.",
        }
        return mapping.get(reason, "Login not permitted.")


    @staticmethod
    def validate_user(user) -> LoginValidationResult:
        """
        Returns LoginValidationResult(ok: bool, reason: str).

        Nothing here performs login. Only performs validation.

        This function is shared by:
        - ConsoleLoginView
        - ApiLoginView
        - CustomAccountAdapter.login()
        - CustomSocialAccountAdapter.save_user()
        - Any future mobile / SPA / magic-link login APIs
        """
        # 1. Null safety
        if not user:
            return LoginValidationResult(False, "USER_NOT_FOUND")

        # 2. Soft-delete check
        if getattr(user, "deleted_at", None) is not None:
            return LoginValidationResult(False, "ACCOUNT_DELETED")

        # 3. Active flag
        if not getattr(user, "is_active", False):
            return LoginValidationResult(False, "ACCOUNT_INACTIVE")

        # 4. Email / SSO verification
        if not getattr(user, "is_verified", False):
            return LoginValidationResult(False, "EMAIL_NOT_VERIFIED")

        # If all checks pass
        return LoginValidationResult(True, None)
