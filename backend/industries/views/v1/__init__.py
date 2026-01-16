from django.urls import include, path

urlpatterns = [
    path("crud/", include("industries.views.v1.crud")),
    path("read/", include("industries.views.v1.read")),
]
