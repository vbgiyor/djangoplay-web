import logging
from django.conf import settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from utilities.constants.unsubscribe import CATEGORY_BY_PREFIX, SYSTEM_EMAIL_PREFIXES
from utilities.admin.url_utils import get_site_base_url
from allauth.account.models import EmailAddress


logger = logging.getLogger(__name__)

UNSUBSCRIBE_TOKEN_CACHE_TTL = 60 * 60 * 24  # 24 hours

class UnsubscribeService:
    """
    ============================================================================
    UNSUBSCRIBE MANAGEMENT SERVICE
    ----------------------------------------------------------------------------
    Extracted from CustomAccountAdapter.send_mail to enforce DRY rules for:

        • Global unsubscribe (user.is_unsubscribed)
        • System email bypasses
        • Category-based unsubscribe (preferences dict)
        • Generating unsubscribe URLs (uid + token)

    This service ONLY decides permission and URL generation. Email sending,
    template rendering, and contextual injection happen elsewhere.

    ============================================================================
    """

    # ----------------------------------------------------------------------
    # Determine if email is allowed to be sent
    # ----------------------------------------------------------------------
    @staticmethod
    def is_allowed(user, prefix: str) -> bool:
        """
        Determine whether the system is allowed to send a given email type to a user.

        Rules:
        -------
        1. System emails ALWAYS allowed (even if unsubscribed)
        2. Global unsubscribe blocks all non-system emails
        3. Category-specific unsubscribe blocks only the associated category
        """
        # 1. System email: always allowed
        if prefix in SYSTEM_EMAIL_PREFIXES:
            logger.debug("unsubscribe: system email → allowed (prefix=%s)", prefix)
            return True

        if not user:
            # If user is not resolvable, assume allowed since we cannot check preferences
            logger.debug("unsubscribe: user not resolved → allowed")
            return True

        # 2. Global unsubscribe
        if getattr(user, "is_unsubscribed", False):
            logger.info(
                "unsubscribe: blocked — user globally unsubscribed (prefix=%s, user=%s)",
                prefix,
                user.email,
            )
            return False

        # 3. Per-category unsubscribe
        if isinstance(getattr(user, "preferences", None), dict):
            category = CATEGORY_BY_PREFIX.get(prefix)
            if category and user.preferences.get(category) is False:
                logger.info(
                    "unsubscribe: blocked — user opted out of category '%s' (prefix=%s)",
                    category,
                    prefix,
                )
                return False

        return True

    # ----------------------------------------------------------------------
    # Generate unsubscribe URL (same logic as in original adapter)
    # ----------------------------------------------------------------------
    @staticmethod
    def build_unsubscribe_url(user) -> str:
        """
        Generate unsubscribe URL using uid + token.
        Used for:
            • transactional emails
            • marketing emails

        Originally: CustomAccountAdapter._unsubscribe_from_mailing_list
        """        

        # try:
        #     uid = urlsafe_base64_encode(force_bytes(user.pk))
        #     token = default_token_generator.make_token(user)            
        #     path = reverse('frontend:unsubscribe', kwargs={'uidb64': uid, 'token': token})
        #     base_url = get_site_base_url()
        #     return f"{base_url}{path}"
        # except Exception as e:
        #     logger.error("unsubscribe: failed to build unsubscribe URL for %s: %s", user, e)
        #     return "#"

        try:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            # 🔒 store latest token (cache, NOT DB)
            cache_key = f"unsubscribe:last_token:{user.pk}"
            cache.set(cache_key, token, UNSUBSCRIBE_TOKEN_CACHE_TTL)            

            path = reverse(
                "frontend:unsubscribe",
                kwargs={"uidb64": uid, "token": token},
            )
            return f"{get_site_base_url()}{path}"

        except Exception as e:
            logger.error(
                "unsubscribe: failed to build unsubscribe URL for %s: %s",
                user,
                e,
            )
            return ""
