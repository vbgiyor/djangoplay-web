import logging

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from drf_spectacular.utils import extend_schema
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)

def social_login_cancelled_view(request):
    logger.info("Social login cancelled, redirecting to account_login")
    messages.info(request, "Login was cancelled. Please try again.")
    return HttpResponseRedirect(reverse('account_login'))

@extend_schema(exclude=True)
class UserMeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'is_verified': getattr(user, 'is_verified', False),
            'employee_code': getattr(user.employee, 'employee_code', None) if hasattr(user, 'employee') else None,
            'permissions': list(user.get_all_permissions()),
        })

@extend_schema(exclude=True)
class SessionUserMeView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'is_verified': getattr(user, 'is_verified', False),
            'employee_code': getattr(user.employee, 'employee_code', None) if hasattr(user, 'employee') else None,
            'permissions': list(user.get_all_permissions()),
        })
