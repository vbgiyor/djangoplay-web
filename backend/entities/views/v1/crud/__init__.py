from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .entity import EntityViewSet

router = DefaultRouter()
router.register(r"entities", EntityViewSet, basename="entities")

urlpatterns = [
    path("", include(router.urls)),
]
