import logging

from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.contrib.sites.models import Site

logger = logging.getLogger(__name__)

_initialized = False


def ensure_google_socialapp():
    global _initialized
    if _initialized:
        return
    _initialized = True

    client_id = getattr(settings, "GOOGLE_CLIENT_ID", None)
    secret    = getattr(settings, "GOOGLE_CLIENT_SECRET", None)

    if not client_id or not secret:
        logger.warning("[SocialApp] Missing Google OAuth credentials.")
        return

    try:
        site = Site.objects.get(id=settings.SITE_ID)
    except Site.DoesNotExist:
        logger.error("[SocialApp] Invalid SITE_ID, cannot bind SocialApp.")
        return

    # ------------------------------------------------------------------
    # ENFORCE EXACTLY ONE GOOGLE SOCIALAPP GLOBALLY
    # ------------------------------------------------------------------
    qs = SocialApp.objects.filter(provider="google")

    if qs.count() > 1:
        keep = qs.first()
        qs.exclude(id=keep.id).delete()
        logger.warning("[SocialApp] Duplicate Google apps removed.")
        qs = SocialApp.objects.filter(provider="google")

    GOOGLE_APP_SETTINGS = {
        "scope": [
            "profile",
            "email",
        ],
        "auth_params": {
            "access_type": "online",
        },
    }
    if qs.exists():
        app = qs.first()
    else:
        app = SocialApp.objects.create(
            provider="google",
            name="Google",
            client_id=client_id,
            secret=secret,
            settings=GOOGLE_APP_SETTINGS,
        )
        logger.info("[SocialApp] Created Google SocialApp.")

    # ------------------------------------------------------------------
    # FAIL FAST: ensure email scope is always present
    # ------------------------------------------------------------------
    scope = (app.settings or {}).get("scope", [])
    if "email" not in scope:
        raise RuntimeError(
            "Google SocialApp misconfigured: 'email' scope is required for SSO"
        )
    # ------------------------------------------------------------------
    # UPDATE CREDENTIALS IF NECESSARY
    # ------------------------------------------------------------------
    updated_fields = []

    if app.client_id != client_id:
        app.client_id = client_id
        updated_fields.append("client_id")

    if app.secret != secret:
        app.secret = secret
        updated_fields.append("secret")

    if app.settings != GOOGLE_APP_SETTINGS:
        app.settings = GOOGLE_APP_SETTINGS
        updated_fields.append("settings")

    if updated_fields:
        app.save(update_fields=updated_fields)
        logger.info(f"[SocialApp] Updated fields: {updated_fields}")

    # ------------------------------------------------------------------
    # ENSURE SITE ASSOCIATION IS EXACTLY THE CURRENT SITE
    # ------------------------------------------------------------------
    app.sites.set([site])
    logger.info(
        f"[SocialApp] Bound to site '{site.domain}' (id={site.id})"
        "[SocialApp] Google settings verified: scope=%s auth_params=%s",
        app.settings.get("scope"),
        app.settings.get("auth_params"),
    )
