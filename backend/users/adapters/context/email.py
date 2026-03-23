from django.conf import settings


class EmailContextProvider:

    """
    Canonical email context shared across ALL email types.
    Must be injected BEFORE template rendering.
    """

    @staticmethod
    def get():
        return {
            # ----------------------------------------------------------------
            # Site
            # ----------------------------------------------------------------
            "site_name": getattr(settings, "SITE_NAME", "DjangoPlay"),

            # ----------------------------------------------------------------
            # Design tokens — injected into every email template automatically.
            # To restyle all emails, change values here only.
            # Never hardcode these hex values directly in HTML templates.
            # ----------------------------------------------------------------

            # Button
            "btn_bg":        "#464b92",
            "btn_color":     "#ffffff",

            # Brand accents (links, unsubscribe, highlights)
            "primary_color": "#464b92",

            # Text
            "muted_color":   "#6c757d",   # pre-header, secondary text
            "body_color":    "#333333",   # main body copy

            # Structure
            "divider_color": "#dcdcdc",
            "footer_bg":     "#F1F7FF",

            # Code / URL blocks
            "code_bg":       "#f4f4f5",
            "code_border":   "#dcdcdc",

            # Fonts
            "body_font":     "'Roboto', Arial, sans-serif",
            "mono_font":     "'Roboto Mono', 'Courier New', monospace",
        }