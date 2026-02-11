from django.urls import path

from .employee import EmployeeDetailAPIView
from .password_reset_request import PasswordResetRequestDetailAPIView
from .signup_request import SignUpRequestDetailAPIView

urlpatterns = [
    path("employees/<int:pk>/", EmployeeDetailAPIView.as_view()),
    path("signup-requests/<int:pk>/", SignUpRequestDetailAPIView.as_view()),
    path("password-reset-requests/<int:pk>/", PasswordResetRequestDetailAPIView.as_view()),
]
