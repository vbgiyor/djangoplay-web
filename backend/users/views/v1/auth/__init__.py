from django.urls import path

from .audit import AuthLogView
from .csrf import CSRFTokenView
from .jwt import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    RedocTokenVerifyView,
)

app_name = "users_v1_auth"

urlpatterns = [
    path("token/", CustomTokenObtainPairView.as_view()),
    path("token/refresh/", CustomTokenRefreshView.as_view()),
    path("token/verify/", RedocTokenVerifyView.as_view()),
    path("csrf/", CSRFTokenView.as_view()),
    path("log/", AuthLogView.as_view()),
]
