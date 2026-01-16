from django.urls import path

from .entity import EntityDetailAPIView

urlpatterns = [
    path("entities/<int:pk>/", EntityDetailAPIView.as_view()),
]
