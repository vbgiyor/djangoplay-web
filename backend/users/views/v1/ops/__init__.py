from django.urls import path

from .export import EmployeeExportAPIView

app_name = "users_v1_ops"

urlpatterns = [
    path("export/employees/", EmployeeExportAPIView.as_view()),
]
