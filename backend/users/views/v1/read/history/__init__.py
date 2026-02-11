from django.urls import path

from .employee import EmployeeHistoryAPIView
from .password_reset_request import PasswordResetRequestHistoryAPIView
from .signup_request import SignUpRequestHistoryAPIView

urlpatterns = [
    path("employees/", EmployeeHistoryAPIView.as_view()),
    path("signup-requests/", SignUpRequestHistoryAPIView.as_view()),
    path("password-reset-requests/", PasswordResetRequestHistoryAPIView.as_view()),
]
