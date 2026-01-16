from django.conf import settings
from django.urls import resolve, reverse


def report_bug_context(request):
    enabled = getattr(settings, 'REPORT_BUG_ENABLED', True)
    if not enabled:
        return {'show_bug_report': False}

    try:
        url_name = resolve(request.path_info).url_name
    except:
        url_name = None

    enabled_urls = getattr(settings, 'REPORT_BUG_ENABLED_ON_URLS', [])
    show = url_name in enabled_urls

    return {
        'show_bug_report': show,
        'report_bug_submit_url': reverse('frontend:report_bug'),
    }
