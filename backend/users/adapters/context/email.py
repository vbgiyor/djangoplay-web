from django.conf import settings


class EmailContextProvider:

    """
    Canonical email context shared across ALL email types.
    Must be injected BEFORE template rendering.
    """

    @staticmethod
    def get():
        return {
            "site_name": getattr(settings, "SITE_NAME", "DjangoPlay"),
        }
