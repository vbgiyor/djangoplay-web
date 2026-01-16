from django.urls import path

from .city import CustomCityHistoryAPIView
from .country import CustomCountryHistoryAPIView
from .global_region import GlobalRegionHistoryAPIView
from .region import CustomRegionHistoryAPIView
from .subregion import CustomSubRegionHistoryAPIView
from .timezone import TimezoneHistoryAPIView

urlpatterns = [
    path("global-regions/", GlobalRegionHistoryAPIView.as_view()),
    path("countries/", CustomCountryHistoryAPIView.as_view()),
    path("regions/", CustomRegionHistoryAPIView.as_view()),
    path("subregions/", CustomSubRegionHistoryAPIView.as_view()),
    path("cities/", CustomCityHistoryAPIView.as_view()),
    path("timezones/", TimezoneHistoryAPIView.as_view()),
]
