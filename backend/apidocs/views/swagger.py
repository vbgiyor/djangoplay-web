import logging

from django.shortcuts import redirect, render
from django.urls import reverse
from drf_spectacular.views import SpectacularSwaggerView as BaseSwaggerView
from policyengine.components.permissions import ActionBasedPermission
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from utilities.constants.template_registry import TemplateRegistry

logger = logging.getLogger(__name__)

class CustomSpectacularSwaggerView(BaseSwaggerView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    template_name = TemplateRegistry.APIDOCS_SWAGGER

    def get(self, request, *args, **kwargs):
        logger.info("Processing GET in CustomSpectacularSwaggerView")
        u_param = 'true' if request.user.is_authenticated else 'false'
        redirect_url = f"{reverse('frontend:api_login')}?u={u_param}&from=api"

        if not request.user.is_authenticated:
            logger.info("Unauthenticated user, redirecting to api_login")
            return redirect(redirect_url)
        if request.user.is_superuser or request.user.has_perm('apidocs.view_swagger'):
            logger.info(f"User {request.user.email} (superuser: {request.user.is_superuser}) accessing Swagger UI.")
            return super().get(request, *args, **kwargs)
        logger.warning("Permission denied in SwaggerView GET, rendering 403.html")
        context = {
            'request': request,
            'form': None,
            'messages': request._messages if hasattr(request, '_messages') else [],
            'from': 'api',
            'u': u_param
        }
        return render(request, TemplateRegistry.ACCOUNT_403, context, status=403)

    def check_permissions(self, request):
        logger.info("Checking permissions in CustomSpectacularSwaggerView")
        u_param = 'true' if request.user.is_authenticated else 'false'
        redirect_url = f"{reverse('frontend:api_login')}?u={u_param}&from=api"

        if not request.user.is_authenticated:
            logger.info("Unauthenticated user, redirecting to api_login")
            return redirect(redirect_url)
        if not (request.user.is_superuser or request.user.has_perm('apidocs.view_swagger')):
            logger.warning("Permission denied in SwaggerView, rendering 403.html")
            context = {
                'request': request,
                'form': None,
                'messages': request._messages if hasattr(request, '_messages') else [],
                'from': 'api',
                'u': u_param
            }
            return render(request, TemplateRegistry.ACCOUNT_403, context, status=403)
        return super().check_permissions(request)

    def handle_exception(self, exc):
        logger.error(f"Handling exception in CustomSpectacularSwaggerView: {exc}, type: {type(exc)}")
        u_param = 'true' if self.request.user.is_authenticated else 'false'
        context = {
            'request': self.request,
            'form': None,
            'messages': self.request._messages if hasattr(self.request, '_messages') else [],
            'from': 'api',
            'u': u_param
        }
        return render(self.request, TemplateRegistry.ACCOUNT_403, context, status=403)

class SwaggerUIView(APIView):
    authentication_classes = [BasicAuthentication, JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, ActionBasedPermission]

    def get(self, request, *args, **kwargs):
        logger.info("Processing GET in SwaggerUIView")
        u_param = 'true' if request.user.is_authenticated else 'false'
        redirect_url = f"{reverse('frontend:api_login')}?u={u_param}"

        if not request.user.is_authenticated:
            logger.info("Unauthenticated user, redirecting to api_login")
            return redirect(redirect_url)
        if request.user.is_authenticated and request.user.is_superuser:
            logger.info(f"Superuser {request.user.email} accessing Swagger UI without restriction.")
            context = {
                'swagger_ui_css': 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css',
                'swagger_ui_bundle': 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js',
                'swagger_ui_standalone': 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone.js',
                'template_name_js': 'drf_spectacular/swagger-ui.js',
                'url': '/api/v1/schema/',
                'title': 'DjangoPlay API',
            }
            return render(request, TemplateRegistry.APIDOCS_SWAGGER, context)
        for permission in self.get_permissions():
            if not permission.has_permission(request, self):
                logger.warning("Permission denied in SwaggerUIView, rendering 403.html")
                request.session['from_swagger'] = True
                context = {
                    'request': request,
                    'form': None,
                    'messages': request._messages if hasattr(request, '_messages') else [],
                    'from': 'api',
                    'u': u_param
                }
                return render(request, TemplateRegistry.ACCOUNT_403, context, status=403)
        context = {
            'swagger_ui_css': 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css',
            'swagger_ui_bundle': 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js',
            'swagger_ui_standalone': 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone.js',
            'template_name_js': 'drf_spectacular/swagger-ui.js',
            'url': '/api/v1/schema/',
            'title': 'DjangoPlay API',
        }
        return render(request, TemplateRegistry.APIDOCS_SWAGGER, context)
