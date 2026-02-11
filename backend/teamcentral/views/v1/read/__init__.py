from django.urls import include, path

app_name = "teamcentral_v1_read"

urlpatterns = [
    path("list/", include("teamcentral.views.v1.read.list")),
    path("detail/", include("teamcentral.views.v1.read.detail")),
    path("history/", include("teamcentral.views.v1.read.history")),
]
