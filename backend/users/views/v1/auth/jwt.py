import logging

from apidocs.utils.querysanitizer import add_sanitization_filter_to_logger
from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from utilities.api.rate_limits import TokenThrottle

logger = logging.getLogger(__name__)
add_sanitization_filter_to_logger(logger)


class CustomTokenObtainSerializer(TokenObtainPairSerializer):
    username_field = "username"

    def validate(self, attrs):
        username = attrs.get("username")
        if username and "@" in username:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(email__iexact=username)
                attrs["username"] = user.username
            except User.DoesNotExist:
                pass
        return super().validate(attrs)


@extend_schema(tags=["Authentication: JWT"])
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainSerializer
    permission_classes = [AllowAny]
    throttle_classes = [TokenThrottle]

    @extend_schema(
        summary="Obtain JWT Token Pair",
        description="""
        Authenticate with username/email and password to get JWT tokens.
        Accepts `username` or `email` as login identifier.
        """,
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "username": {"type": "string"},
                    "password": {"type": "string"},
                    "remember_me": {"type": "boolean"},
                },
                "required": ["username", "password"],
            }
        },
        responses={
            200: OpenApiResponse(
                description="Success",
                response={
                    "type": "object",
                    "properties": {
                        "access": {"type": "string"},
                        "refresh": {"type": "string"},
                    },
                },
            ),
            401: OpenApiResponse(description="Invalid credentials"),
        },
    )
    def post(self, request, *args, **kwargs):
        mutable_data = request.data.copy()
        username = mutable_data.get("username")
        remember_me = mutable_data.get("remember_me", False)

        logger.info(f"JWT login attempt for: {username} | remember_me: {remember_me}")

        serializer = self.get_serializer(data=mutable_data)
        try:
            serializer.is_valid(raise_exception=True)
            logger.info(f"JWT login SUCCESS for: {username}")
        except Exception as e:
            logger.warning(f"JWT login FAILED for: {username} -> {e}")
            return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

        response_data = serializer.validated_data

        if remember_me:
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(serializer.user)
            refresh.access_token.set_exp(
                lifetime=settings.SIMPLE_JWT.get(
                    "REFRESH_TOKEN_LIFETIME_REMEMBER_ME"
                )
            )
            response_data["refresh"] = str(refresh)

        return Response(response_data, status=status.HTTP_200_OK)


@extend_schema(exclude=True, tags=["Authentication: JWT"])
class CustomTokenRefreshView(TokenRefreshView):

    @extend_schema(
        summary="Refresh JWT Access Token",
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "access": {"type": "string"},
                        "refresh": {"type": "string"},
                    },
                }
            )
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(exclude=True)
class RedocTokenVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return Response({"valid": True})
