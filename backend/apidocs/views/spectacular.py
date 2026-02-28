import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.shortcuts import render
from drf_spectacular.views import SpectacularAPIView as BaseSchemaView
from rest_framework.exceptions import PermissionDenied
from utilities.constants.template_registry import TemplateRegistry

logger = logging.getLogger(__name__)

class CustomSpectacularAPIView(BaseSchemaView):
    def check_permissions(self, request):
        logger.debug("Checking permissions in CustomSpectacularAPIView")
        for permission in self.get_permissions():
            if not permission.has_permission(request, self):
                logger.debug("Permission denied in APIView, rendering 403.html")
                context = {
                    'request': request,
                    'form': None,
                    'messages': request._messages if hasattr(request, '_messages') else [],
                }
                response = render(request, TemplateRegistry.ACCOUNT_403, context, status=403)
                logger.debug(f"APIView response: {response.content[:1000]}")
                return response
        return super().check_permissions(request)

    def handle_exception(self, exc):
        logger.debug(f"Handling exception in CustomSpectacularAPIView: {exc}, type: {type(exc)}")
        if isinstance(exc, PermissionDenied | DjangoPermissionDenied):
            logger.debug("PermissionDenied caught in APIView, rendering 403_login.html")
            context = {
                'request': self.request,
                'form': None,
                'messages': self.request._messages if hasattr(self.request, '_messages') else [],
            }
            response = render(self.request, TemplateRegistry.ACCOUNT_403, context, status=403)
            logger.debug(f"APIView exception response: {response.content[:1000]}")
            return response
        return super().handle_exception(exc)
