from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .industry import IndustryViewSet

router = DefaultRouter()
router.register(r"industries", IndustryViewSet, basename="industry")

urlpatterns = [
    path("", include(router.urls)),
]
