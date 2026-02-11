import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

# from teamcentral.models import MemberProfile
from teamcentral.models import MemberProfile
from utilities.constants.template_registry import TemplateRegistry

logger = logging.getLogger(__name__)

@login_required
def dashboard_view(request, app_label=None):
    if app_label:
        app_display_name = settings.APP_DISPLAY_NAMES.get(app_label, app_label.title())
    else:
        app_display_name = None

    if request.session.get('first_time_signup', False):
        messages.success(request, "You have successfully signed up.")
        del request.session['first_time_signup']

    members = MemberProfile.objects.filter(deleted_at__isnull=True, is_active=True)
    context = {
        "app_display_name": app_display_name or True,
        'members': members,
        'user': request.user,
    }
    return render(request, TemplateRegistry.CONSOLE_DASHBOARD, context)
