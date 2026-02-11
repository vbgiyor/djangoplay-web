from django.urls import include, path

app_name = "helpdesk_v1_read"

urlpatterns = [
    path("list/", include("helpdesk.views.v1.read.list")),
    path("detail/", include("helpdesk.views.v1.read.detail")),
    path("history/", include("helpdesk.views.v1.read.history")),
]
