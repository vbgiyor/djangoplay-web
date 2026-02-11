from django.urls import path

from .bulk_update import (
    DepartmentBulkUpdateAPIView,
    RoleBulkUpdateAPIView,
    TeamBulkUpdateAPIView,
)

app_name = "users_v1_ops"

urlpatterns = [
    path("bulk/departments/", DepartmentBulkUpdateAPIView.as_view()),
    path("bulk/roles/", RoleBulkUpdateAPIView.as_view()),
    path("bulk/teams/", TeamBulkUpdateAPIView.as_view()),
]
