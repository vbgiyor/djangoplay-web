from django.urls import path

from .autocomplete import (
    AddressAutocomplete,
    DepartmentAutocomplete,
    LeaveTypeAutocomplete,
    MemberProfileAutocomplete,
    RoleAutocomplete,
    TeamAutocomplete,
)

app_name = "teamcentral_v1_ui"

urlpatterns = [
    path("addresses/", AddressAutocomplete.as_view()),
    path("departments/", DepartmentAutocomplete.as_view()),
    path("teams/", TeamAutocomplete.as_view()),
    path("roles/", RoleAutocomplete.as_view()),
    path("members/", MemberProfileAutocomplete.as_view()),
    path("leave-types/", LeaveTypeAutocomplete.as_view()),
]
