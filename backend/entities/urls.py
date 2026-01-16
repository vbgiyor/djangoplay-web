from django.urls import include, path

urlpatterns = [
    path("", include("entities.views.v1")),
]
