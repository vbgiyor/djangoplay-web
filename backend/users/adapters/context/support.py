from django.conf import settings


class SupportContextProvider:

    """
    ============================================================================
    SUPPORT CONTEXT PROVIDER
    ----------------------------------------------------------------------------
    Centralizes support metadata (email, phone, GitHub, LinkedIn, address).

    Used by:
        • EmailEngine
        • Any transactional email context
        • Any template requiring consistent footer/contact details
    ============================================================================
    """

    @staticmethod
    def get():
        """
        Returns a context dict with support info.
        """
        return {
            "support_email": settings.SUPPORT_EMAIL,
            "support_phone": getattr(settings, "SUPPORT_PHONE", ""),
            "support_location": getattr(settings, "SUPPORT_LOCATION", ""),
            "linkedin_url": getattr(settings, "LINKEDIN_URL", ""),
            "github_url": getattr(settings, "GITHUB_URL", ""),
        }
