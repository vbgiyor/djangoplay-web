from django.urls import include, path

urlpatterns = [
    path(
        "list/",
        include("fincore.views.v1.read.list"),
    ),
    path(
        "detail/",
        include("fincore.views.v1.read.detail"),
    ),
    path(
        "history/",
        include("fincore.views.v1.read.history"),
    ),
]
