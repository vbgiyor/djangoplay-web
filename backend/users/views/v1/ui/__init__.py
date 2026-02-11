from django.urls import path

from .autocomplete import EmployeeAutocomplete

app_name = "users_v1_ui"

urlpatterns = [
    path("employees/", EmployeeAutocomplete.as_view()),
]
