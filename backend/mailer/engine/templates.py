import logging
from django.template.loader import render_to_string

from utilities.constants.template_registry import TemplateRegistry as T

logger = logging.getLogger(__name__)


class TemplateResolver:
    """
    ============================================================================
    EMAIL TEMPLATE RESOLVER
    ----------------------------------------------------------------------------
    Central template loader extracted from CustomAccountAdapter._render_template.

    Responsibilities:
    - Normalize external / framework prefixes (e.g. allauth)
    - Resolve canonical project template prefixes via TemplateRegistry
    - Apply fallback rules consistently

    Lookup order:
        Primary:
            account/email/{prefix}{suffix}

        Fallback (TEXT + SUBJECT only):
            account/fallback/{prefix}{suffix}

        HTML:
            No fallback — missing HTML is a hard error
    ============================================================================
    """

    # ------------------------------------------------------------------
    # Prefix normalization (framework → canonical)
    # ------------------------------------------------------------------
    PREFIX_ALIASES = {
        "password_reset_key": T.PASSWORD_RESET_EMAIL,
    }


    def __init__(self, prefix: str):
        self.original_prefix = prefix
        self.prefix = self._normalize_prefix(prefix)

    def _normalize_prefix(self, prefix: str) -> str:
        """
        Normalize framework-specific prefixes to canonical project prefixes.
        """
        normalized = self.PREFIX_ALIASES.get(prefix, prefix)

        if normalized != prefix:
            logger.info(
                "TemplateResolver: normalized email prefix '%s' → '%s'",
                prefix,
                normalized,
            )

        return normalized


    def render(self, suffix: str, context: dict) -> str:
        """
        Resolve email template with semantic directory rules:

        - HTML → email/ only (no fallback)
        - subject/text → email/ preferred, fallback/ authoritative
        """
        if suffix == ".html":
            primary = f"account/email/{self.prefix}{suffix}"
            try:
                return render_to_string(primary, context)
            except Exception as e:
                logger.exception(
                    "EMAIL TEMPLATE RENDER FAILED",
                    extra={
                        "template": primary,
                        "prefix": self.prefix,
                        "suffix": suffix,
                        "context_keys": sorted(context.keys()),
                    },
                )
                raise


        # SUBJECT / TEXT
        primary = f"account/email/{self.prefix}{suffix}"
        try:
            return render_to_string(primary, context)
        except Exception:
            logger.debug(
                "TemplateResolver: primary template missing, trying fallback "
                "(prefix=%s suffix=%s)",
                self.prefix,
                suffix,
            )

        fallback = f"account/fallback/{self.prefix}{suffix}"
        try:
            return render_to_string(fallback, context)
        except Exception as e:
            logger.exception(
                "EMAIL TEMPLATE RENDER FAILED",
                extra={
                    "template": primary,
                    "prefix": self.prefix,
                    "suffix": suffix,
                    "context_keys": sorted(context.keys()),
                },
            )
            raise

