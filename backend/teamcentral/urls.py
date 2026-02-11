from django.urls import include, path
from utilities.views.health_check import HealthCheckView

app_name = "teamcentral"

urlpatterns = [
    path("", include("teamcentral.views.v1")),
    path("health/", HealthCheckView.as_view(), name="health-check"),
]
