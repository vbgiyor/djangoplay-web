
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

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logger.info(f"Logging out user: {request.user}")

        # Let Allauth perform logout + redirect resolution
        response = super().post(request, *args, **kwargs)

        host = request.get_host()
        from_param = request.GET.get("from")

        # Swagger / ReDoc overrides
        if from_param == "swagger":
            return redirect(f"{reverse('frontend:api_login')}?from=api")

        if from_param == "redoc":
            return redirect(f"{reverse('frontend:api_login')}?from=redoc")

        # 🔥 Issues subdomain override
        if host.startswith("issues."):
            return redirect("/issues/")

        # Console dashboard → login
        if request.path.startswith("/console/"):
            return redirect(reverse("account_login"))

        return response
