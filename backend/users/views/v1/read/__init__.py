# users/views/v1/read/__init__.py

from django.urls import include, path

app_name = "users_v1_read"

urlpatterns = [
    path("list/", include("users.views.v1.read.list")),
    path("detail/", include("users.views.v1.read.detail")),
    path("history/", include("users.views.v1.read.history")),
]
