from django.urls import path

from .autocomplete import (
    BugReportAutocomplete,
    SupportTicketAutocomplete,
)

app_name = "helpdesk_v1_ui"

urlpatterns = [
    path("supports/", SupportTicketAutocomplete.as_view()),
    path("bugs/", BugReportAutocomplete.as_view()),
]
