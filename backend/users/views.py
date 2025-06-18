import logging

from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from rest_framework import permissions, status, views, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import UserSerializer

logger = logging.getLogger(__name__)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.get_active_users().order_by('id')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ['username', 'email']

    def create(self, request, *args, **kwargs):
        logger.info(f"Creating user: {request.data.get('username')}")
        request.data['created_by'] = request.user.id
        try:
            response = super().create(request, *args, **kwargs)
            logger.info(f"User created: {request.data.get('username')}")
            return response
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise

    def update(self, request, *args, **kwargs):
        logger.info(f"Updating user: {kwargs.get('pk')}")
        instance = self.get_object()
        if 'username' in request.data:
            request.data['username'] = instance.username
        if 'email' in request.data and request.user.email == request.data['email']:
            logger.warning(f"User {request.user.username} attempted to update own email")
            return Response({"error": "Cannot update own email."}, status=status.HTTP_400_BAD_REQUEST)
        email = request.data.get('email')
        if email and User.objects.filter(email=email).exclude(id=instance.id).exists():
            logger.warning(f"Email {email} already in use.")
            return Response({"error": "Email already in use."}, status=status.HTTP_400_BAD_REQUEST)
        request.data['updated_by'] = request.user.id
        try:
            response = super().update(request, *args, **kwargs)
            logger.info(f"User {instance.username} updated")
            return response
        except ValidationError as e:
            logger.error(f"Error updating user: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        logger.info(f"Disabling user: {kwargs.get('pk')}")
        try:
            instance = User.all_users.get(id=kwargs.get('pk'))
            instance.soft_delete()
            instance.is_active = False
            instance.updated_by = request.user
            instance.save()
            logger.info(f"User {instance.username} disabled")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except User.DoesNotExist:
            logger.error(f"User with id {kwargs.get('pk')} not found")
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error disabling user {kwargs.get('pk')}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class SignupView(views.APIView):
    permission_classes = [AllowAny]

    def get_tokens_for_user(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            'refresh_token': str(refresh),
            'access_token': str(refresh.access_token)
        }

    def post(self, request, *args, **kwargs):
        logger.info(f"Signup attempt: {request.data.get('username')}")
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                tokens = self.get_tokens_for_user(user)
                logger.info(f"User {user.username} signed up")
                return Response({'user': serializer.data, 'tokens': tokens}, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                logger.error(f"Error signing up user: {e}")
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        logger.warning(f"Invalid signup: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        logger.info(f"Login attempt: {request.data.get('username')}")
        username = request.data.get('username')
        password = request.data.get('password')
        if not username:
            logger.warning("Username required")
            return Response({'error': 'Username required'}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            logger.warning("Password required")
            return Response({'error': 'Password required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            logger.warning(f"User not found: {username}")
            return Response({'error': 'User does not exist'}, status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(username=username, password=password)
        if user and user.is_active:
            logger.info(f"User {username} authenticated")
            refresh = RefreshToken.for_user(user)
            return Response({
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh)
            }, status=status.HTTP_200_OK)
        logger.warning(f"Authentication failed: {username}")
        return Response({'error': 'Authentication failed'}, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        logger.info(f"Password reset: {request.user.username}")
        user = request.user
        password = request.data.get("password")
        if not password or len(password) < 8:
            logger.warning(f"Invalid password length: {user.username}")
            return Response({'error': 'Password must be at least 8 characters'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(password)
        user.save()
        tokens = self.get_tokens_for_user(user)
        logger.info(f"Password reset: {user.username}")
        return Response({'status': 'Password updated', 'tokens': tokens}, status=status.HTTP_200_OK)

    def get_tokens_for_user(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            'refresh_token': str(refresh),
            'access_token': str(refresh.access_token)
        }
