from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import LoginView, PasswordResetView, SignupView, UserViewSet

# Create a router and register the UserViewSet
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    # URL for Signup
    path('signup/', SignupView.as_view(), name='signup'),

    # URL for Login
    path('login/', LoginView.as_view(), name='login'),

    # URL for Password Reset
    path(
        'password-reset/',
        PasswordResetView.as_view(),
        name='password-reset'),

    # Register the UserViewSet routes
] + router.urls
