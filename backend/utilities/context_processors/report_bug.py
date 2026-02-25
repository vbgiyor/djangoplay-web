from django.conf import settings
from django.urls import NoReverseMatch, resolve, reverse


def report_bug_context(request):
    # Global feature flag
    enabled = getattr(settings, 'REPORT_BUG_ENABLED', True)
    if not enabled:
        return {'show_bug_report': False, 'report_bug_submit_url': None}

    # Current URL name (if resolvable)
    try:
        url_name = resolve(request.path_info).url_name
    except Exception:
        url_name = None

    enabled_urls = getattr(settings, 'REPORT_BUG_ENABLED_ON_URLS', [])
    show = url_name in enabled_urls

    # Reverse safely — some hosts may not have 'frontend' namespace
    try:
        report_bug_url = reverse('frontend:report_bug')
    except NoReverseMatch:
        report_bug_url = None

    return {
        'show_bug_report': show and report_bug_url is not None,
        'report_bug_submit_url': report_bug_url,
    }
