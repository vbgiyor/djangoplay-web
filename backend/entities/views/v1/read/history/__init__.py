from django.urls import path

from .entity import EntityHistoryAPIView

urlpatterns = [
    path("entities/", EntityHistoryAPIView.as_view()),
]
