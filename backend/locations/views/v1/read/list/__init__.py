from django.urls import path

from .city import CityListAPIView
from .country import CountryListAPIView
from .global_region import GlobalRegionListAPIView
from .location import LocationListAPIView
from .region import RegionListAPIView
from .subregion import SubRegionListAPIView
from .timezone import TimezoneListAPIView

app_name = "locations_v1_read_list"

urlpatterns = [
    path("global-regions/", GlobalRegionListAPIView.as_view()),
    path("countries/", CountryListAPIView.as_view()),
    path("regions/", RegionListAPIView.as_view()),
    path("subregions/", SubRegionListAPIView.as_view()),
    path("cities/", CityListAPIView.as_view()),
    path("locations/", LocationListAPIView.as_view()),
    path("timezones/", TimezoneListAPIView.as_view()),
]
