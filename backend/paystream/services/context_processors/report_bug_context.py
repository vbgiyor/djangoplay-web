from django.conf import settings
from django.urls import NoReverseMatch, resolve, reverse


def report_bug_context(request):
    """
    Context processor for the 'Report Bug' feature.

    Returns:
        show_bug_report (bool) – whether to show the report bug link
        report_bug_submit_url (str|None) – URL to submit the bug report

    """
    if not getattr(settings, 'REPORT_BUG_ENABLED', True):
        return {'show_bug_report': False, 'report_bug_submit_url': None}

    try:
        url_name = resolve(request.path_info).url_name
    except Exception:
        url_name = None

    enabled_urls = getattr(settings, 'REPORT_BUG_ENABLED_ON_URLS', [])
    show = url_name in enabled_urls

    try:
        report_bug_url = reverse('frontend:report_bug')
    except NoReverseMatch:
        report_bug_url = None

    return {
        'show_bug_report': show and report_bug_url is not None,
        'report_bug_submit_url': report_bug_url,
    }
