from django.urls import path

from .employee import EmployeeListAPIView
from .password_reset_request import PasswordResetRequestListAPIView
from .signup_request import SignUpRequestListAPIView

urlpatterns = [

    path("employees/", EmployeeListAPIView.as_view()),
    path("signup-requests/", SignUpRequestListAPIView.as_view()),
    path("password-reset-requests/", PasswordResetRequestListAPIView.as_view()),
]
