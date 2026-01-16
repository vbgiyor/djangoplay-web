from django.urls import include, path

urlpatterns = [
    path("list/", include("industries.views.v1.read.list")),
    path("detail/", include("industries.views.v1.read.detail")),
    path("history/", include("industries.views.v1.read.history")),
]
