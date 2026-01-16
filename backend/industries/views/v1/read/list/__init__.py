from django.urls import path

from .industry import IndustryListAPIView

urlpatterns = [
    path("industries/", IndustryListAPIView.as_view()),
]
