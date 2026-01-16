
import logging

from allauth.account.views import LogoutView
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView
from utilities.constants.template_registry import TemplateRegistry

logger = logging.getLogger(__name__)

import logging

logger = logging.getLogger(__name__)

class CustomLogoutView(LogoutView):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logger.info(f"Logging out user: {request.user}")

        for _message in messages.get_messages(request):
            pass

        super().post(request, *args, **kwargs)

        from_param = request.GET.get('from')

        if from_param == 'swagger':
            return redirect(f"{reverse('frontend:api_login')}?from=api")
        if from_param == 'redoc':
            return redirect(f"{reverse('frontend:api_login')}?from=redoc")

        # DASHBOARD → GO TO LOGIN
        if request.path.startswith('/console/dashboard/') or request.path == '/console/dashboard/':
            return redirect(reverse('account_login'))

        # ALL OTHER → SHOW LOGOUT PAGE
        return redirect('frontend:logout_done')


class LogoutSuccessView(TemplateView):
    template_name = TemplateRegistry.CONSOLE_LOGOUT

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['login_url'] = reverse('account_login')
        return context
