from django.urls import include, path

urlpatterns = [
    path("", include("industries.views.v1")),
]
