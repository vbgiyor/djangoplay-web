from django.urls import include, path

app_name = "locations_v1_read"

urlpatterns = [
    path("list/", include("locations.views.v1.read.list")),
    path("detail/", include("locations.views.v1.read.detail")),
    path("history/", include("locations.views.v1.read.history")),
]
