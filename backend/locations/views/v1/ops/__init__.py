from django.urls import path

from .bulk_update import (
    CityBulkUpdateAPIView,
    CustomCountryBulkUpdateAPIView,
    CustomRegionBulkUpdateAPIView,
    CustomSubRegionBulkUpdateAPIView,
    GlobalRegionBulkUpdateAPIView,
    TimezoneBulkUpdateAPIView,
)
from .export import CityExportAPIView

urlpatterns = [
    path("bulk/global-regions/", GlobalRegionBulkUpdateAPIView.as_view()),
    path("bulk/countries/", CustomCountryBulkUpdateAPIView.as_view()),
    path("bulk/regions/", CustomRegionBulkUpdateAPIView.as_view()),
    path("bulk/subregions/", CustomSubRegionBulkUpdateAPIView.as_view()),
    path("bulk/cities/", CityBulkUpdateAPIView.as_view()),
    path("bulk/timezones/", TimezoneBulkUpdateAPIView.as_view()),
    path("export/cities/", CityExportAPIView.as_view()),
]
