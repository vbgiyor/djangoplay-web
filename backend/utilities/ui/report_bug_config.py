# Report Bug config to specify which pages, bug reporting provision shall appear on.

from django.conf import settings


class ReportBugConfig:
    ENABLED = getattr(settings, 'REPORT_BUG_ENABLED', True)

    # ONLY read from settings – no default list
    ENABLED_ON_URLS = getattr(settings, 'REPORT_BUG_ENABLED_ON_URLS', [])

    SUPPORT_EMAIL = getattr(settings, 'SUPPORT_EMAIL', settings.DEFAULT_FROM_EMAIL)

    MAX_ATTACHMENT_SIZE_MB = getattr(settings, 'REPORT_BUG_MAX_ATTACHMENT_SIZE_MB', 10)
    ALLOWED_FILE_TYPES = getattr(settings, 'REPORT_BUG_ALLOWED_FILE_TYPES', [
        'image/jpeg', 'image/png', 'application/pdf', 'text/plain', 'text/log'
    ])
