from django.urls import path

from .industry import IndustryHistoryAPIView

urlpatterns = [
    path("industries/", IndustryHistoryAPIView.as_view()),
]
