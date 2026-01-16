from django.urls import path

from .autocomplete import (
    CityAutocomplete,
    CustomCountryAutocomplete,
    CustomRegionAutocomplete,
    CustomSubRegionAutocomplete,
    GlobalRegionAutocomplete,
    TimezoneAutocomplete,
)

urlpatterns = [
    path("global-regions/", GlobalRegionAutocomplete.as_view()),
    path("countries/", CustomCountryAutocomplete.as_view()),
    path("regions/", CustomRegionAutocomplete.as_view()),
    path("subregions/", CustomSubRegionAutocomplete.as_view()),
    path("cities/", CityAutocomplete.as_view()),
    path("timezones/", TimezoneAutocomplete.as_view()),
]
