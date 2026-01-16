from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .city import CustomCityViewSet
from .country import CustomCountryViewSet
from .global_region import GlobalRegionViewSet
from .location import LocationViewSet
from .region import CustomRegionViewSet
from .subregion import CustomSubRegionViewSet
from .timezone import TimezoneViewSet

app_name = "locations_v1_crud"

router = DefaultRouter()
router.register(r"countries", CustomCountryViewSet, basename="country")
router.register(r"regions", CustomRegionViewSet, basename="region")
router.register(r"subregions", CustomSubRegionViewSet, basename="subregion")
router.register(r"cities", CustomCityViewSet, basename="city")
router.register(r"locations", LocationViewSet, basename="location")
router.register(r"timezones", TimezoneViewSet, basename="timezone")
router.register(r"global-regions", GlobalRegionViewSet, basename="global-region")

urlpatterns = [
    path("", include(router.urls)),
]
