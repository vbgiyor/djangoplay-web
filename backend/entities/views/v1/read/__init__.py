from django.urls import include, path

urlpatterns = [
    path("list/", include("entities.views.v1.read.list")),
    path("detail/", include("entities.views.v1.read.detail")),
    path("history/", include("entities.views.v1.read.history")),
]
