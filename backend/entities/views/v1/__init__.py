from django.urls import include, path

app_name = "entities_v1"


urlpatterns = [
    path("crud/", include("entities.views.v1.crud")),
    path("read/", include("entities.views.v1.read")),
    path("ui/", include("entities.views.v1.ui")),
]
