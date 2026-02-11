from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .employee import EmployeeViewSet
from .signup_request import SignUpRequestViewSet

app_name = "users_v1_crud"

router = DefaultRouter()
router.register(r"employees", EmployeeViewSet)
router.register(r"signup-requests", SignUpRequestViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
