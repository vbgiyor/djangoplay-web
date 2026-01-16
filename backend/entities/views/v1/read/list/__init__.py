from django.urls import path

from .entity import EntityListAPIView

urlpatterns = [
    path("entities/", EntityListAPIView.as_view()),
]
