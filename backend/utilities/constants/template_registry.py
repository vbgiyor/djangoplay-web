from policyengine.commons.base import get_user_role
from policyengine.models import FeatureFlag


class TemplateRegistry:

    """
    Central registry for template names used across the project.

    - For templates that need permission/feature-flag logic, expose dedicated
      helper methods (e.g., get_api_stats_template).
    - For normal templates, expose simple constants plus a generic get_template()
      as a single place to later plug in overrides/branding/etc.
    """

    # -------------------------------------------------------------------------
    # APIDOCS: SPECIALISED HELPERS
    # -------------------------------------------------------------------------

    @classmethod
    def get_api_stats_template(cls, user):
        """
        Decide which API stats template to use for a given user.

        - Anonymous or flag disabled → public stats
        - Flag enabled + role in {DJGO, CEO, SSO} → personal template
        - Everyone else → public stats
        """
        if not user.is_authenticated:
            return cls.APIDOCS_STATS_PUBLIC

        try:
            flag = FeatureFlag.objects.get(key="apidocs_stats_view")
            if not flag.is_enabled_for(user):
                return cls.APIDOCS_STATS_PUBLIC
        except FeatureFlag.DoesNotExist:
            return cls.APIDOCS_STATS_PUBLIC

        role = get_user_role(user)
        if role in {"DJGO", "CEO", "SSO"}:
            return cls.APIDOCS_STATS_PERSONAL

        return cls.APIDOCS_STATS_PUBLIC

    # -------------------------------------------------------------------------
    # GENERIC RESOLVER
    # -------------------------------------------------------------------------

    @classmethod
    def get_template(cls, template_name: str) -> str:
        """
        Generic resolver for templates that don't need any permission or dynamic
        switching. Currently just returns the name unchanged, but this gives us
        a single place to plug in:
        - per-tenant branding
        - A/B tests
        - theme-specific overrides, etc.
        """
        return template_name

    # -------------------------------------------------------------------------
    # APIDOCS TEMPLATES
    # -------------------------------------------------------------------------

    # API stats (public vs personal)
    APIDOCS_STATS_PUBLIC = "api_stats_public.html"
    APIDOCS_STATS_PERSONAL = "api_stats_private.html"

    # API documentation consoles
    APIDOCS_SWAGGER = "drf_spectacular/swagger.html"
    APIDOCS_REDOC = "drf_spectacular/redoc.html"

    # -------------------------------------------------------------------------
    # SHARED / COMMON TEMPLATES
    # -------------------------------------------------------------------------

    ACCOUNT_401 = "account/site_pages/401.html"
    ACCOUNT_403 = "account/site_pages/403.html"
    ACCOUNT_404 = "account/site_pages/404.html"

    # -------------------------------------------------------------------------
    # FRONTEND / CONSOLE TEMPLATES
    # -------------------------------------------------------------------------
    # Use concise names for common console views. Keep these action-focused
    # (CONSOLE_LOGIN, CONSOLE_LOGOUT) rather than app-prefixed names.

    CONSOLE_LOGIN_FORM = "account/site_pages/login.html"
    CONSOLE_LOGOUT = "account/site_pages/logout.html"
    API_LOGIN_FORM = "account/site_pages/api_login.html"

    PASSWORD_RESET_TAB = CONSOLE_LOGIN_FORM
    PASSWORD_RESET_FORM = "account/site_pages/password_reset_confirm.html"

    SUPPORT_REQUEST_FORM = "account/site_pages/support.html"
    CONSOLE_DASHBOARD = "account/site_pages/dashboard.html"
    UNSUBSCRIBE = "account/site_pages/unsubscribe.html"

    APACHE_LICENSE = "account/site_pages/license.html"  # if you prefer license served under account pages
    # (if you serve license via views.license.license_file_view you can still keep FileResponse)


    # -------------------------------------------------------------------------
    # EMAIL TEMPLATES (canonical template *prefixes* used by adapter.send_mail)
    # -------------------------------------------------------------------------
    # Canonical template prefixes used by send_email_via_adapter / adapters.send_mail.
    # Adapter will compose full filenames by appending suffixes such as:
    #   - "_subject.txt"         (subject fallback)
    #   - ".txt"                 (text body)
    #   - ".html"                (html body)
    #
    # Use short prefix names (no path, no ".html"). Adapter will resolve:
    #   account/email/{prefix}.html
    #   account/email/{prefix}_subject.txt
    #   account/email/{prefix}.txt
    #
    # Welcome / Signup (welcome / signup-success email)
    EMAIL_SIGNUP_SUCCESS = "account_signup"            # resolves to account/email/account_signup.html

    # Verification emails
    EMAIL_VERIFICATION_MANUAL = "account_manual_verification"         # resolves to account/email/verification_email.html
    EMAIL_VERIFICATION_SSO = "account_sso_verification"  # resolves to account/email/account_verification.html

    # Support / confirmation templates (bugs/support)
    REQUEST_TO_SUPPORT_EMAIL = "request_to_support"     # resolves to account/email/request_to_support.html
    CONFIRMATION_TO_USER_EMAIL = "confirmation_to_user" # resolves to account/email/confirmation_to_user.html

    # -------------------------------------------------------------------------
    # PASSWORD RESET (allauth compatibility)
    # -------------------------------------------------------------------------
    # NOTE:
    # allauth requires the password-reset *subject* template to be resolvable
    # from account/email/. Subject fallback is ignored for this flow.
    # So use account/email/password_reset_subject.txt, instead of account/fallback/password_reset_subject.txt
    PASSWORD_RESET_EMAIL = "password_reset"
