from django.urls import path

from .autocomplete import (
    AddressAutocomplete,
    DepartmentAutocomplete,
    EmployeeAutocomplete,
    LeaveTypeAutocomplete,
    MemberAutocomplete,
    RoleAutocomplete,
    SupportAutocomplete,
    TeamAutocomplete,
)

app_name = "users_v1_ui"

urlpatterns = [
    path("employees/", EmployeeAutocomplete.as_view()),
    path("members/", MemberAutocomplete.as_view()),
    path("departments/", DepartmentAutocomplete.as_view()),
    path("teams/", TeamAutocomplete.as_view()),
    path("roles/", RoleAutocomplete.as_view()),
    path("addresses/", AddressAutocomplete.as_view()),
    path("leave-types/", LeaveTypeAutocomplete.as_view()),
    path("supports/", SupportAutocomplete.as_view()),
]
