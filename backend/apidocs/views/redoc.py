import json
import logging

from django.shortcuts import redirect, render
from django.urls import reverse
from drf_spectacular.views import SpectacularRedocView
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from utilities.constants.template_registry import TemplateRegistry

logger = logging.getLogger(__name__)

class CustomSpectacularRedocView(SpectacularRedocView):
    template_name = TemplateRegistry.APIDOCS_REDOC
    authentication_classes = [BasicAuthentication, JWTAuthentication, SessionAuthentication]
    # permission_classes = [IsAuthenticated]
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        logger.info("Processing GET in CustomSpectacularRedocView")
        u_param = 'true' if request.user.is_authenticated else 'false'
        # redirect_url = f"{reverse('frontend:api_login')}?u={u_param}&from=redoc"
        next_url = reverse('apidocs:redoc')
        redirect_url = f"{reverse('frontend:api_login')}?u={u_param}&from=redoc&next={next_url}"

        if not request.user.is_authenticated:
            logger.info("Unauthenticated user, redirecting to api_login")
            return redirect(redirect_url)

        if request.user.is_superuser or request.user.has_perm('apidocs.view_redoc'):
            logger.info(f"User {request.user.email} accessing Redoc UI")
            return super().get(request, *args, **kwargs)

        logger.warning("Permission denied in ReDocView GET, rendering 403.html")
        context = {
            'request': request,
            'form': None,
            'messages': request._messages if hasattr(request, '_messages') else [],
            'from': 'redoc',
            'u': u_param
        }
        logger.info(
            "REDOC DEBUG user=%s auth=%s",
            request.user,
            request.user.is_authenticated
        )
        return render(request, TemplateRegistry.ACCOUNT_403, context, status=403)

    def check_permissions(self, request):
        logger.info("Checking permissions in CustomSpectacularRedocView")
        u_param = 'true' if request.user.is_authenticated else 'false'
        # redirect_url = f"{reverse('frontend:api_login')}?u={u_param}&from=redoc"
        next_url = reverse('apidocs:redoc')
        redirect_url = f"{reverse('frontend:api_login')}?u={u_param}&from=redoc&next={next_url}"

        if not request.user.is_authenticated:
            logger.info("Unauthenticated user, redirecting to api_login")
            return redirect(redirect_url)
        if not (request.user.is_superuser or request.user.has_perm('apidocs.view_redoc')):
            logger.warning("Permission denied in ReDocView, rendering 403.html")
            context = {
                'request': request,
                'form': None,
                'messages': request._messages if hasattr(request, '_messages') else [],
                'from': 'redoc',
                'u': u_param
            }
            return render(request, TemplateRegistry.ACCOUNT_403, context, status=403)
        return super().check_permissions(request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        redoc_settings = {
            "scrollYOffset": 0,
            "hideDownloadButton": False,
        }
        context["settings_json"] = json.dumps(redoc_settings)
        return context

    def handle_exception(self, exc):
        logger.error(f"Handling exception in CustomSpectacularRedocView: {exc}, type: {type(exc)}")
        u_param = 'true' if self.request.user.is_authenticated else 'false'
        context = {
            'request': self.request,
            'form': None,
            'messages': self.request._messages if hasattr(self.request, '_messages') else [],
            'from': 'redoc',
            'u': u_param
        }
        return render(self.request, TemplateRegistry.ACCOUNT_403, context, status=403)
