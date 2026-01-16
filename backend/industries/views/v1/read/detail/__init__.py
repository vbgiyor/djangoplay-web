from django.urls import path

from .industry import IndustryDetailAPIView

urlpatterns = [
    path("industries/<int:pk>/", IndustryDetailAPIView.as_view()),
]
