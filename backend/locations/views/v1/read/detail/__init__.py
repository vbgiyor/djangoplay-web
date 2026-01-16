from django.urls import path

from .city import CityDetailAPIView
from .country import CustomCountryDetailAPIView
from .global_region import GlobalRegionDetailAPIView
from .location import LocationDetailAPIView
from .region import CustomRegionDetailAPIView
from .subregion import CustomSubRegionDetailAPIView
from .timezone import TimezoneDetailAPIView

urlpatterns = [
    path("global-regions/<int:pk>/", GlobalRegionDetailAPIView.as_view()),
    path("countries/<int:pk>/", CustomCountryDetailAPIView.as_view()),
    path("regions/<int:pk>/", CustomRegionDetailAPIView.as_view()),
    path("subregions/<int:pk>/", CustomSubRegionDetailAPIView.as_view()),
    path("cities/<int:pk>/", CityDetailAPIView.as_view()),
    path("locations/<int:pk>/", LocationDetailAPIView.as_view()),
    path("timezones/<int:pk>/", TimezoneDetailAPIView.as_view()),
]
